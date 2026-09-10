"""
SiteSync AI — DB Seeder (API-Based Embeddings)

Reads data/baseline_schedule.csv, embeds all activity descriptions
using the API-based embedder (Azure OpenAI → NVIDIA NIM → n-gram),
and inserts into SQLite.

Run with: uv run python -m sitesync.db.seed
NO heavy downloads required — uses API calls only.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import numpy as np
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

console = Console()


def embed_descriptions(descriptions: list[str]) -> list[bytes]:
    """Embed a list of strings using the API-based embedder → list of BLOB bytes."""
    from sitesync.linking.embedder import embed_text_passage, serialize

    console.print("[cyan]Embedding via API (Azure OpenAI → NVIDIA NIM → n-gram fallback)...[/cyan]")

    embeddings = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Embedding schedule activities...", total=len(descriptions))
        for desc in descriptions:
            vec = embed_text_passage(desc)
            embeddings.append(serialize(vec))
            progress.advance(task)

    return embeddings


def _safe_float(val: str) -> float | None:
    """Convert a string to float, returning None if not numeric."""
    if not val or not val.strip():
        return None
    try:
        return float(val.strip())
    except (ValueError, TypeError):
        return None


def main():
    import sitesync  # noqa: F401  — triggers .env loading
    from sitesync.config import settings
    from sitesync.db.models import Base, ScheduleActivity
    from sitesync.db.session import get_db, engine

    csv_path = Path("data/baseline_schedule.csv")
    if not csv_path.exists():
        console.print(f"[red]CSV not found: {csv_path}[/red]")
        sys.exit(1)

    # ── Create tables if they don't exist ─────────────────────────────────────
    Base.metadata.create_all(bind=engine)
    console.print("[green]✅ Database tables created/verified[/green]")

    # ── Read CSV ──────────────────────────────────────────────────────────────
    rows: list[dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    console.print(f"[green]Read {len(rows)} activities from CSV[/green]")

    # ── Embed descriptions ────────────────────────────────────────────────────
    descriptions = [r["description"] for r in rows]
    embeddings = embed_descriptions(descriptions)

    # ── Insert into DB ────────────────────────────────────────────────────────
    with get_db() as db:
        # Clear existing data (idempotent seed)
        deleted = db.query(ScheduleActivity).delete()
        if deleted:
            console.print(f"[yellow]Cleared {deleted} existing activities[/yellow]")

        for row, emb_blob in zip(rows, embeddings):
            activity = ScheduleActivity(
                activity_id=row["activity_id"].strip(),
                wbs_code=row.get("wbs_code", "").strip() or None,
                discipline=row["discipline"].strip(),
                description=row["description"].strip(),
                location=row.get("location", "").strip() or None,
                planned_start=row.get("planned_start", "").strip() or None,
                planned_end=row.get("planned_end", "").strip() or None,
                progress_pct=_safe_float(row.get("progress_pct", "0")) or 0.0,
                predecessor_id=row.get("predecessor_id", "").strip() or None,
                unit_of_measure=row.get("unit_of_measure", "").strip() or None,
                quantity_planned=_safe_float(row.get("quantity_planned", "")),
                embedding=emb_blob,
            )
            db.add(activity)

        console.print(f"[green]✅ Seeded {len(rows)} activities into SQLite[/green]")

    # ── Summary table ─────────────────────────────────────────────────────────
    table = Table(title="Schedule Seed Summary", show_header=True, header_style="bold cyan")
    table.add_column("Discipline")
    table.add_column("Count", justify="right")

    discipline_counts: dict[str, int] = {}
    for row in rows:
        d = row["discipline"]
        discipline_counts[d] = discipline_counts.get(d, 0) + 1

    for disc, cnt in sorted(discipline_counts.items()):
        table.add_row(disc, str(cnt))
    table.add_row("[bold]TOTAL[/bold]", f"[bold]{len(rows)}[/bold]")
    console.print(table)


if __name__ == "__main__":
    main()
