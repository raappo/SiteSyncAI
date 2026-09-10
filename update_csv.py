import pandas as pd
import random
from datetime import datetime, timedelta

activities = [
    # Civil
    ("CIVIL-001", "Civil", "Site grading and leveling", "Zone A", "2026-01-01", 30, 100),
    ("CIVIL-002", "Civil", "Excavation for column footings", "Zone A", "2026-02-01", 45, 100),
    ("CIVIL-003", "Civil", "Formwork and reinforcement for foundations", "Zone A", "2026-03-15", 30, 80),
    ("CIVIL-004", "Civil", "Concrete pouring for foundations", "Zone A", "2026-04-15", 15, 0),
    ("CIVIL-005", "Civil", "Backfilling and compaction", "Zone A", "2026-05-01", 30, 0),
    # Piping
    ("PIPING-001", "Piping", "Prefabrication of 6-inch hot oil line spools", "Offsite Shop", "2026-02-01", 60, 100),
    ("PIPING-002", "Piping", "Erect and weld spools on 6-inch hot oil line", "Tank Farm", "2026-04-01", 90, 40),
    ("PIPING-003", "Piping", "NDT and hydrotesting of hot oil line", "Tank Farm", "2026-07-01", 30, 0),
    ("PIPING-004", "Piping", "Insulation of hot oil line", "Tank Farm", "2026-08-01", 30, 0),
    # Electrical
    ("ELEC-001", "Electrical", "Installation of main ground grid", "Site-Wide", "2026-03-01", 60, 90),
    ("ELEC-002", "Electrical", "Install cable trays and conduits", "Unit 1", "2026-05-01", 90, 20),
    ("ELEC-003", "Electrical", "Pulling MV/LV cables", "Unit 1", "2026-08-01", 60, 0),
    ("ELEC-004", "Electrical", "Substation equipment installation", "Substation", "2026-04-01", 120, 50),
    # Instrumentation
    ("INST-001", "Instrumentation", "Install transmitters and control loops", "Tank Farm", "2026-07-01", 60, 0),
    ("INST-002", "Instrumentation", "JB installation and cable termination", "Tank Farm", "2026-09-01", 45, 0),
    ("INST-003", "Instrumentation", "Loop checking and pre-commissioning", "Tank Farm", "2026-10-15", 30, 0),
    # HSE
    ("HSE-001", "HSE", "Site safety induction for all personnel", "Site-Wide", "2026-01-01", 365, 50),
    ("HSE-002", "HSE", "Daily toolbox talks and permit auditing", "Site-Wide", "2026-01-01", 365, 50),
    ("HSE-003", "HSE", "Monthly safety committee review", "Site-Wide", "2026-01-30", 330, 40),
]

data = []
for aid, disc, desc, loc, start_str, dur, prog in activities:
    start_date = datetime.strptime(start_str, "%Y-%m-%d")
    end_date = start_date + timedelta(days=dur)
    data.append({
        "Activity ID": aid,
        "Discipline": disc,
        "Description": desc,
        "Location": loc,
        "Planned Start": start_date.strftime("%Y-%m-%d"),
        "Planned End": end_date.strftime("%Y-%m-%d"),
        "Progress %": prog
    })

df = pd.DataFrame(data)
df.to_csv("data/baseline_schedule.csv", index=False)
print("Updated baseline_schedule.csv")
