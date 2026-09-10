"""
Database seed script.
Reads the baseline schedule and populates the database.
"""
from __future__ import annotations

import csv
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
    """Seed the database from a Pandas DataFrame."""
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
            desc = str(row.get("Description", ""))
            if not desc:
                continue

            vector = embed_text_passage(desc)

            activity = ScheduleActivity(
                activity_id=str(row.get("Activity ID", f"ACT-{count}")),
                discipline=str(row.get("Discipline", "Unknown")),
                description=desc,
                location=str(row.get("Location", "")),
                planned_start=str(row.get("Planned Start", "")),
                planned_end=str(row.get("Planned End", "")),
                progress_pct=float(row.get("Progress %", 0.0)),
                embedding=serialize(vector),
            )
            db.add(activity)
            count += 1

        db.commit()
        console.print(f"[green]Successfully seeded {count} activities into the schedule.[/green]")

def run_seed():
    """Seed the database from the default baseline CSV."""
    # BUG FIX: Use absolute path relative to this file
    base_dir = Path(__file__).resolve().parent.parent.parent
    csv_path = base_dir / "data" / "baseline_schedule.csv"

    if not csv_path.exists():
        console.print(f"[red]Error: Could not find {csv_path}[/red]")
        sys.exit(1)

    console.print(f"Reading baseline from {csv_path}...")
    df = pd.read_csv(csv_path)
    seed_from_dataframe(df, overwrite=True)

if __name__ == "__main__":
    run_seed()
