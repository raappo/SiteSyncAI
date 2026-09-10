"""
SiteSync AI — LLM Discovery & Benchmark Script

Phase 0.5: Dynamically discovers NVIDIA NIM models and benchmarks both
NVIDIA NIM and Experiential Labs endpoints on:
  - Time-to-First-Token (TTFT)
  - Total latency
  - Strict JSON schema adherence (ActivityUpdate schema)

Auto-updates .env with NVIDIA_DEFAULT_MODEL and EXPLABS_FALLBACK_MODEL.

Run with: uv run python scripts/benchmark_llms.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

# ── Bootstrap ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

console = Console()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
EXPLABS_API_KEY = os.getenv("EXPLABS_API_KEY", "")
EXPLABS_BASE_URL = os.getenv("EXPLABS_BASE_URL", "https://api.experientiallabs.ai/v1")

# ── Benchmark prompt ───────────────────────────────────────────────────────────
BENCHMARK_PROMPT = """You are an AI assistant for an infrastructure project management system.
Extract structured data from this site diary entry and return ONLY valid JSON matching this exact schema:

{
  "discipline": "<Civil|Piping|Electrical|Instrumentation|HSE>",
  "location": "<site location string>",
  "activity_description": "<normalized activity description>",
  "actual_progress_pct": <float 0-100>,
  "date": "<YYYY-MM-DD>",
  "evidence_type": "<text|spreadsheet|scanned_doc|photo>"
}

Site diary entry:
"Spool erected on 6 inch line near hot oil tank. Done 3 joints weld today, total 9 joints done out of 28. Date: 14-Feb-2024."

Return ONLY the JSON object, no markdown, no explanation."""

EXPECTED_KEYS = {"discipline", "location", "activity_description", "actual_progress_pct", "date", "evidence_type"}


# ── Candidate models ───────────────────────────────────────────────────────────
EXPLABS_CANDIDATES = [
    "laguna-xs-2.1-free",
    "nemotron-3-nano-omni-30b-a3b-reasoning-free",
    "gemma-4-26b-a4b-it-free",
    "llama-4-maverick-17b-128e-instruct-fp8-free",
    "qwen3-8b-a0.6b-instruct-free",
]

# NVIDIA chat-compatible model prefixes to look for
NVIDIA_CHAT_PREFIXES = [
    "meta/llama", "nvidia/llama", "mistralai/", "google/gemma",
    "microsoft/phi", "qwen/", "deepseek/", "nvidia/nemotron",
]


@dataclass
class BenchmarkResult:
    provider: str
    model: str
    ttft_ms: float = 0.0
    total_ms: float = 0.0
    json_valid: bool = False
    schema_complete: bool = False
    schema_score: float = 0.0  # fraction of expected keys present
    error: str = ""
    raw_response: str = ""
    composite_score: float = field(init=False, default=0.0)

    def __post_init__(self):
        # Composite: 50% schema adherence, 30% TTFT penalty, 20% JSON validity
        if self.error:
            self.composite_score = 0.0
        else:
            ttft_score = max(0.0, 1.0 - (self.ttft_ms / 10000))  # normalize to 10s
            self.composite_score = (
                (0.5 * self.schema_score)
                + (0.3 * ttft_score)
                + (0.2 * float(self.json_valid))
            )


def discover_nvidia_models() -> list[str]:
    """Query NVIDIA NIM /models endpoint and filter for chat-compatible models."""
    if not NVIDIA_API_KEY:
        console.print("[yellow]⚠ No NVIDIA_API_KEY — skipping NVIDIA discovery[/yellow]")
        return []

    console.print("[cyan]🔍 Discovering NVIDIA NIM models...[/cyan]")
    try:
        resp = requests.get(
            f"{NVIDIA_BASE_URL}/models",
            headers={"Authorization": f"Bearer {NVIDIA_API_KEY}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        all_models = [m["id"] for m in data.get("data", [])]

        # Filter for chat-compatible models
        chat_models = [
            m for m in all_models
            if any(m.startswith(prefix) or prefix in m for prefix in NVIDIA_CHAT_PREFIXES)
        ]

        console.print(f"[green]Found {len(all_models)} total, {len(chat_models)} chat-compatible models[/green]")

        # Prefer larger/instruct variants, take top 5
        priority = [
            m for m in chat_models if any(
                kw in m.lower() for kw in ["70b", "405b", "nemotron-70", "llama-3.1"]
            )
        ]
        rest = [m for m in chat_models if m not in priority]
        ranked = (priority + rest)[:5]

        console.print(f"[cyan]Top NVIDIA candidates:[/cyan] {ranked}")
        return ranked

    except Exception as e:
        console.print(f"[red]NVIDIA model discovery failed: {e}[/red]")
        # Fallback to known good models
        fallbacks = [
            "meta/llama-3.1-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "mistralai/mistral-7b-instruct-v0.3",
        ]
        console.print(f"[yellow]Using fallback candidates: {fallbacks}[/yellow]")
        return fallbacks


def benchmark_model(
    provider: str, model: str, base_url: str, api_key: str
) -> BenchmarkResult:
    """Send benchmark prompt to a single model and measure performance."""
    result = BenchmarkResult(provider=provider, model=model)

    if not api_key:
        result.error = "No API key"
        return result

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": BENCHMARK_PROMPT}],
        "max_tokens": 300,
        "temperature": 0.1,
        "stream": True,  # needed for TTFT measurement
    }

    t_start = time.perf_counter()
    t_first_token = None
    content_chunks: list[str] = []

    try:
        with requests.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            stream=True,
            timeout=60,
        ) as resp:
            if resp.status_code == 429:
                result.error = "Rate limited (429)"
                return result
            if resp.status_code not in (200, 201):
                result.error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                return result

            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                if line.startswith("data: "):
                    line = line[6:]
                if line.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(line)
                    delta = chunk["choices"][0]["delta"].get("content", "")
                    if delta:
                        if t_first_token is None:
                            t_first_token = time.perf_counter()
                            result.ttft_ms = (t_first_token - t_start) * 1000
                        content_chunks.append(delta)
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue

        result.total_ms = (time.perf_counter() - t_start) * 1000
        result.raw_response = "".join(content_chunks)

        # ── Validate JSON schema adherence ─────────────────────────────────
        # Strip markdown fences if present
        clean = re.sub(r"```(?:json)?|```", "", result.raw_response).strip()
        try:
            parsed = json.loads(clean)
            result.json_valid = True
            present_keys = set(parsed.keys()) & EXPECTED_KEYS
            result.schema_score = len(present_keys) / len(EXPECTED_KEYS)
            result.schema_complete = present_keys == EXPECTED_KEYS
        except json.JSONDecodeError:
            result.json_valid = False
            result.schema_score = 0.0

        # Recalculate composite after setting values
        result.__post_init__()

    except requests.exceptions.Timeout:
        result.error = "Timeout (60s)"
    except Exception as e:
        result.error = str(e)[:100]

    return result


def update_env_file(env_path: Path, updates: dict[str, str]) -> None:
    """Update key=value pairs in the .env file."""
    content = env_path.read_text(encoding="utf-8")
    for key, value in updates.items():
        pattern = re.compile(rf'^{key}=.*$', re.MULTILINE)
        new_line = f'{key}="{value}"'
        if pattern.search(content):
            content = pattern.sub(new_line, content)
        else:
            content += f"\n{new_line}\n"
    env_path.write_text(content, encoding="utf-8")


def main():
    console.rule("[bold cyan]SiteSync AI — LLM Benchmark[/bold cyan]")

    # ── Discover NVIDIA models ─────────────────────────────────────────────
    nvidia_models = discover_nvidia_models()
    # Limit to top 3 for benchmark efficiency
    nvidia_top3 = nvidia_models[:3]

    # ── Run benchmarks ─────────────────────────────────────────────────────
    all_results: list[BenchmarkResult] = []

    console.print(f"\n[bold]Benchmarking {len(nvidia_top3)} NVIDIA + {min(3, len(EXPLABS_CANDIDATES))} Experiential Labs models...[/bold]\n")

    # NVIDIA
    for model in nvidia_top3:
        console.print(f"  → NVIDIA: [yellow]{model}[/yellow]", end=" ")
        r = benchmark_model("NVIDIA", model, NVIDIA_BASE_URL, NVIDIA_API_KEY)
        console.print(f"TTFT={r.ttft_ms:.0f}ms  JSON={r.json_valid}  Score={r.composite_score:.3f}" if not r.error else f"[red]{r.error}[/red]")
        all_results.append(r)

    # Experiential Labs
    for model in EXPLABS_CANDIDATES[:3]:
        console.print(f"  → ExpLabs: [yellow]{model}[/yellow]", end=" ")
        r = benchmark_model("ExpLabs", model, EXPLABS_BASE_URL, EXPLABS_API_KEY)
        console.print(f"TTFT={r.ttft_ms:.0f}ms  JSON={r.json_valid}  Score={r.composite_score:.3f}" if not r.error else f"[red]{r.error}[/red]")
        all_results.append(r)

    # ── Results table ──────────────────────────────────────────────────────
    table = Table(title="LLM Benchmark Results", show_header=True, header_style="bold magenta")
    table.add_column("Provider")
    table.add_column("Model", max_width=45)
    table.add_column("TTFT (ms)", justify="right")
    table.add_column("Total (ms)", justify="right")
    table.add_column("JSON ✓", justify="center")
    table.add_column("Schema %", justify="right")
    table.add_column("Score", justify="right")
    table.add_column("Error")

    for r in sorted(all_results, key=lambda x: x.composite_score, reverse=True):
        table.add_row(
            r.provider,
            r.model,
            f"{r.ttft_ms:.0f}" if not r.error else "—",
            f"{r.total_ms:.0f}" if not r.error else "—",
            "✅" if r.json_valid else "❌",
            f"{r.schema_score * 100:.0f}%" if not r.error else "—",
            f"[bold green]{r.composite_score:.3f}[/bold green]" if r.composite_score > 0 else "[red]0.000[/red]",
            r.error[:40] if r.error else "",
        )

    console.print(table)

    # ── Pick winners and update .env ───────────────────────────────────────
    nvidia_results = [r for r in all_results if r.provider == "NVIDIA" and not r.error]
    explabs_results = [r for r in all_results if r.provider == "ExpLabs" and not r.error]

    env_updates: dict[str, str] = {}

    if nvidia_results:
        best_nvidia = max(nvidia_results, key=lambda r: r.composite_score)
        env_updates["NVIDIA_DEFAULT_MODEL"] = best_nvidia.model
        console.print(f"\n🏆 [bold green]Best NVIDIA model:[/bold green] {best_nvidia.model} (score={best_nvidia.composite_score:.3f})")
    else:
        console.print("\n[yellow]⚠ No working NVIDIA models found — check API key / rate limits[/yellow]")
        # Use a sensible default
        env_updates["NVIDIA_DEFAULT_MODEL"] = "meta/llama-3.1-70b-instruct"

    if explabs_results:
        best_explabs = max(explabs_results, key=lambda r: r.composite_score)
        env_updates["EXPLABS_FALLBACK_MODEL"] = best_explabs.model
        console.print(f"🏆 [bold green]Best ExpLabs model:[/bold green] {best_explabs.model} (score={best_explabs.composite_score:.3f})")
    else:
        console.print("[yellow]⚠ No working ExpLabs models found[/yellow]")
        env_updates["EXPLABS_FALLBACK_MODEL"] = "laguna-xs-2.1-free"

    # Update .env
    env_path = ROOT / ".env"
    update_env_file(env_path, env_updates)
    console.print(f"\n[green]✅ Updated .env with winning models[/green]")
    console.print(f"   NVIDIA_DEFAULT_MODEL  = {env_updates.get('NVIDIA_DEFAULT_MODEL', 'unchanged')}")
    console.print(f"   EXPLABS_FALLBACK_MODEL = {env_updates.get('EXPLABS_FALLBACK_MODEL', 'unchanged')}")

    # Save results as JSON for audit trail
    results_path = ROOT / "data" / "benchmark_results.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, "w") as f:
        json.dump(
            [
                {
                    "provider": r.provider,
                    "model": r.model,
                    "ttft_ms": r.ttft_ms,
                    "total_ms": r.total_ms,
                    "json_valid": r.json_valid,
                    "schema_score": r.schema_score,
                    "composite_score": r.composite_score,
                    "error": r.error,
                }
                for r in all_results
            ],
            f,
            indent=2,
        )
    console.print(f"[dim]Results saved to {results_path}[/dim]")


if __name__ == "__main__":
    main()
