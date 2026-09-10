"""
SiteSync AI — Full Pipeline Integration Test

Runs the complete end-to-end pipeline without the UI:
  text input → extraction → linking → routing → memory

Usage: uv run python scripts/run_pipeline_test.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.rule import Rule
from rich.panel import Panel

console = Console()


def main():
    console.print(Panel.fit(
        "[bold cyan]SiteSync AI — End-to-End Pipeline Test[/bold cyan]\n"
        "[dim]Text → LLM Extract → Fuzzy Link → Route → Memory[/dim]",
        border_style="cyan"
    ))

    # ── 0. Hardware info ──────────────────────────────────────────────────────
    console.rule("Hardware Detection")
    from sitesync.utils.hardware import print_device_summary
    print_device_summary()

    # ── 1. Seed DB if empty ───────────────────────────────────────────────────
    console.rule("Database")
    from sitesync.db.models import ScheduleActivity
    from sitesync.db.session import get_db

    with get_db() as db:
        count = db.query(ScheduleActivity).count()

    if count == 0:
        console.print("[yellow]DB empty — running seed...[/yellow]")
        from sitesync.db.seed import main as seed_main
        seed_main()
    else:
        console.print(f"[green]DB OK — {count} activities loaded[/green]")

    # ── 2. Reload matcher embeddings ──────────────────────────────────────────
    from sitesync.linking.matcher import get_matcher
    matcher = get_matcher()
    matcher.refresh()

    # ── 3. Test inputs ────────────────────────────────────────────────────────
    test_cases = [
        {
            "raw": "Spool erected on 6 inch hot oil line. 9 joints done out of 28 total. Date: 14-Feb-2024.",
            "evidence": "text",
            "label": "Piping jargon → PIP-002",
        },
        {
            "raw": "RCC footing pour at grid B3 done. 85 cum poured, QC hold point cleared. 14/02/2024.",
            "evidence": "text",
            "label": "Civil pour → CIV-003",
        },
        {
            "raw": "E&I loop check complete on MCC-04. All interlocks checked and commissioned.",
            "evidence": "text",
            "label": "Instrumentation loop check → INS-005",
        },
    ]

    for i, case in enumerate(test_cases, 1):
        console.rule(f"Test {i}: {case['label']}")
        console.print(f"[dim]Input:[/dim] {case['raw']}")

        # ── Extract ──────────────────────────────────────────────────────────
        console.print("\n[cyan]Step 1: LLM Extraction[/cyan]")
        from sitesync.extraction.extractor import extract
        result = extract(case["raw"], evidence_type=case["evidence"])

        if result.error:
            console.print(f"[red]Extraction failed: {result.error}[/red]")
            # Fallback: create a minimal ActivityUpdate manually for linking test
            from sitesync.extraction.schemas import ActivityUpdate
            updates = []
        else:
            console.print(f"  → {len(result.updates)} update(s) extracted in {result.extraction_ms:.0f}ms")
            for u in result.updates:
                console.print(f"  → [green]{u.discipline}[/green] | {u.activity_description[:60]} | {u.actual_progress_pct:.0f}%")
            updates = result.updates

        # ── Link ─────────────────────────────────────────────────────────────
        if updates:
            console.print("\n[cyan]Step 2: Fuzzy Linking[/cyan]")
            from sitesync.linking.matcher import match
            for u in updates:
                link = match(u, top_k=3)
                if link.best_match:
                    bm = link.best_match
                    console.print(
                        f"  → Best: [bold]{bm.activity_id}[/bold] | "
                        f"sem={bm.semantic_score:.3f} | conf=[bold {'green' if bm.confidence >= 0.85 else 'yellow'}]{bm.confidence:.3f}[/bold {'green' if bm.confidence >= 0.85 else 'yellow'}]"
                    )
                    if len(link.top_matches) > 1:
                        for m in link.top_matches[1:]:
                            console.print(f"       #{m.rank}: {m.activity_id} | conf={m.confidence:.3f}")

                # ── Route ─────────────────────────────────────────────────────
                console.print("\n[cyan]Step 3: Routing[/cyan]")
                from sitesync.routing.router import route
                event = route(link, source_file="pipeline_test")
                if event.auto_applied:
                    console.print(f"  → [green]AUTO-APPLIED[/green] to {event.matched_activity_id}")
                else:
                    console.print(f"  → [yellow]REVIEW QUEUE[/yellow] — conf below threshold")

                # ── Memory ────────────────────────────────────────────────────
                if event.auto_applied and link.best_match:
                    console.print("\n[cyan]Step 4: Institutional Memory[/cyan]")
                    from sitesync.memory.chroma_store import upsert_event, memory_stats
                    upsert_event(
                        event_id=event.id,
                        activity_id=link.best_match.activity_id,
                        discipline=u.discipline,
                        activity_description=u.activity_description,
                        actual_progress_pct=u.actual_progress_pct,
                        report_date=u.date,
                        evidence_type=u.evidence_type,
                        planned_start=link.best_match.planned_start,
                        planned_end=link.best_match.planned_end,
                        constraints=u.constraints,
                        confidence_score=event.confidence_score,
                    )
                    stats = memory_stats()
                    console.print(f"  → Memory records: {stats.get('total_events', 0)}")

    # ── Memory query test ──────────────────────────────────────────────────────
    console.rule("Memory Query Test")
    from sitesync.memory.chroma_store import query_memory, memory_stats
    stats = memory_stats()
    console.print(f"Total memory records: [bold]{stats.get('total_events', 0)}[/bold]")

    if stats.get("total_events", 0) > 0:
        results = query_memory("piping spool weld hot oil line", n_results=3)
        console.print(f"\nQuery: 'piping spool weld hot oil line' → {len(results)} result(s)")
        for r in results:
            console.print(f"  [{r['similarity']:.2f}] {r['document'][:80]}")

    console.print(Panel.fit("[bold green]Pipeline test complete![/bold green]", border_style="green"))


if __name__ == "__main__":
    main()
