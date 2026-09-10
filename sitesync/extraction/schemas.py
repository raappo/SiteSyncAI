"""SiteSync AI — Extraction schemas (Pydantic v2)."""
from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ActivityUpdate(BaseModel):
    """
    Strict JSON payload extracted from any field input.
    This is the canonical output schema of the LLM extraction layer.
    """

    discipline: Literal["Civil", "Piping", "Electrical", "Instrumentation", "HSE"] = Field(
        description="Engineering discipline (Civil/Piping/Electrical/Instrumentation/HSE)"
    )
    location: str = Field(
        description="Physical site location (e.g., 'Tank Farm Area', 'Grid B3')"
    )
    activity_description: str = Field(
        description="Normalized activity description from field report"
    )
    actual_progress_pct: float = Field(
        ge=0.0, le=100.0,
        description="Reported actual progress percentage (0–100)"
    )
    date: str = Field(
        description="Date of the reported activity in YYYY-MM-DD format"
    )
    evidence_type: Literal["text", "spreadsheet", "scanned_doc", "photo"] = Field(
        description="Type of evidence this update came from"
    )
    quantity_completed: Optional[float] = Field(
        default=None,
        description="Absolute quantity completed (if stated, e.g., joints, m3)"
    )
    quantity_unit: Optional[str] = Field(
        default=None,
        description="Unit for quantity_completed (e.g., 'joints', 'm3', 'spools')"
    )
    constraints: Optional[list[str]] = Field(
        default=None,
        description="List of any constraints/blockers mentioned (material shortage, breakdown, etc.)"
    )
    confidence_note: Optional[str] = Field(
        default=None,
        description="Any ambiguity the LLM noted about this extraction"
    )

    @field_validator("date")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Accept YYYY-MM-DD; also try to parse and normalize common formats."""
        import re
        from datetime import datetime
        # Already YYYY-MM-DD?
        if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            return v
        # Try common formats
        for fmt in ("%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%B %d, %Y", "%d %b %Y"):
            try:
                dt = datetime.strptime(v, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date: {v}")

    @field_validator("activity_description")
    @classmethod
    def normalize_description(cls, v: str) -> str:
        """Strip excessive whitespace and title-case for consistency."""
        return " ".join(v.split())

    class Config:
        json_schema_extra = {
            "example": {
                "discipline": "Piping",
                "location": "Tank Farm Area",
                "activity_description": "Erect and weld spool on Line 24-HO-101 (6-inch hot oil)",
                "actual_progress_pct": 32.14,
                "date": "2024-02-14",
                "evidence_type": "text",
                "quantity_completed": 9.0,
                "quantity_unit": "joints",
                "constraints": ["Flange alignment issue on NE side"],
                "confidence_note": None,
            }
        }


class ExtractionResult(BaseModel):
    """Wrapper returned by the extractor, includes raw LLM response for audit."""
    updates: list[ActivityUpdate] = Field(default_factory=list)
    raw_llm_response: str = ""
    model_used: str = ""
    extraction_ms: float = 0.0
    error: Optional[str] = None
