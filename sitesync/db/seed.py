"""
Database seed script.
Reads the baseline schedule and populates the database.

CSV Column Map (baseline_schedule.csv header → seed key):
  activity_id    → "activity_id"
  wbs_code       → "wbs_code"
  discipline     → "discipline"
  description    → "description"
  location       → "location"
  planned_start  → "planned_start"
  planned_end    → "planned_end"
  progress_pct   → "progress_pct"
  predecessor_id → "predecessor_id"
  unit_of_measure→ "unit_of_measure"
  quantity_planned→ "quantity_planned"
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from sitesync.db.models import Base, ScheduleActivity, EventLog, ReviewQueueItem
from sitesync.db.session import engine, get_db
from sitesync.linking.embedder import embed_text_passage, serialize
from rich.console import Console

console = Console()


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def seed_from_dataframe(df: pd.DataFrame, overwrite: bool = True) -> None:
    """
    Seed the database from a Pandas DataFrame.

    Expected columns (matching baseline_schedule.csv):
      activity_id, wbs_code, discipline, description, location,
      planned_start, planned_end, progress_pct,
      predecessor_id, unit_of_measure, quantity_planned
    """
    init_db()

    with get_db() as db:
        if overwrite:
            db.query(ReviewQueueItem).delete()
            db.query(EventLog).delete()
            db.query(ScheduleActivity).delete()
            db.commit()
            console.print("[yellow]Cleared existing schedule data.[/yellow]")

        count = 0
        for _, row in df.iterrows():
            desc = str(row.get("description", ""))
            if not desc or desc == "nan":
                continue

            vector = embed_text_passage(desc)

            # Parse optional numeric fields safely
            def _float(val, default=0.0):
                try:
                    return float(val) if pd.notna(val) else default
                except (ValueError, TypeError):
                    return default

            def _str(val, default=""):
                s = str(val) if pd.notna(val) else default
                return "" if s == "nan" else s

            activity = ScheduleActivity(
                activity_id=_str(row.get("activity_id"), f"ACT-{count}"),
                wbs_code=_str(row.get("wbs_code")),
                discipline=_str(row.get("discipline"), "Unknown"),
                description=desc,
                location=_str(row.get("location")),
                planned_start=_str(row.get("planned_start")),
                planned_end=_str(row.get("planned_end")),
                progress_pct=_float(row.get("progress_pct")),
                predecessor_id=_str(row.get("predecessor_id")),
                unit_of_measure=_str(row.get("unit_of_measure")),
                quantity_planned=_float(row.get("quantity_planned"), None),
                embedding=serialize(vector),
            )
            db.add(activity)
            count += 1

        db.commit()
        console.print(f"[green]Successfully seeded {count} activities into the schedule.[/green]")


def run_seed():
    """Seed the database from the default baseline CSV."""
    base_dir = Path(__file__).resolve().parent.parent.parent
    csv_path = base_dir / "data" / "baseline_schedule.csv"

    if not csv_path.exists():
        console.print(f"[red]Error: Could not find {csv_path}[/red]")
        sys.exit(1)

    console.print(f"Reading baseline from {csv_path}...")
    df = pd.read_csv(csv_path, index_col=False)
    seed_from_dataframe(df, overwrite=True)


# ── Entrypoint alias required by pyproject.toml [project.scripts] ────────────
def main():
    """Entrypoint: uv run sitesync-seed"""
    run_seed()


if __name__ == "__main__":
    main()
