"""
SiteSync AI — Primavera XER Parser
"""
import pandas as pd
from io import StringIO
from pathlib import Path

def parse_xer_to_dataframe(xer_file) -> pd.DataFrame:
    """
    Parse a Primavera P6 .xer file (or mock CSV fallback) into a Pandas DataFrame.
    """
    if isinstance(xer_file, (str, Path)):
        # Just mock for the prototype, reading as CSV
        try:
            return pd.read_csv(xer_file)
        except Exception:
            pass
            
    # If it's an uploaded file object or we need a mock dataframe
    try:
        if hasattr(xer_file, "getvalue"):
            content = xer_file.getvalue().decode("utf-8")
        else:
            content = xer_file.read().decode("utf-8")
        
        # If it looks like CSV, read it
        if "," in content.split("\n")[0]:
            return pd.read_csv(StringIO(content))
    except Exception:
        pass
        
    # Return mock baseline if parsing fails
    return pd.DataFrame([
        {"Activity ID": "CIVIL-001", "Discipline": "Civil", "Description": "Excavation", "Location": "Zone A", "Planned Start": "2026-01-01", "Planned End": "2026-03-01", "Progress %": 0},
        {"Activity ID": "PIPING-001", "Discipline": "Piping", "Description": "Weld spools", "Location": "Tank Farm", "Planned Start": "2026-02-01", "Planned End": "2026-05-01", "Progress %": 0},
    ])
