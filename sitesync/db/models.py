"""
SiteSync AI — SQLAlchemy ORM Models

Three tables:
  - ScheduleActivity  : the L5/L6 baseline plan nodes
  - EventLog          : every field update received (raw + extracted)
  - ReviewQueueItem   : low-confidence events awaiting planner action
"""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class ScheduleActivity(Base):
    """Baseline L5/L6 schedule node from Primavera / MS Project."""

    __tablename__ = "schedule_activity"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_id = Column(String(50), unique=True, nullable=False, index=True)
    wbs_code = Column(String(100), nullable=True)
    discipline = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=False)
    location = Column(String(200), nullable=True)
    planned_start = Column(String(20), nullable=True)  # ISO date string
    planned_end = Column(String(20), nullable=True)
    progress_pct = Column(Float, default=0.0)
    actual_start = Column(String(20), nullable=True)
    actual_end = Column(String(20), nullable=True)
    predecessor_id = Column(String(50), nullable=True)
    unit_of_measure = Column(String(30), nullable=True)
    quantity_planned = Column(Float, nullable=True)
    quantity_actual = Column(Float, default=0.0)

    # Serialized numpy float32 array (384-dim for all-MiniLM-L6-v2)
    embedding = Column(LargeBinary, nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relationships
    event_logs = relationship("EventLog", back_populates="activity", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ScheduleActivity {self.activity_id}: {self.description[:40]}>"


class EventLog(Base):
    """
    Immutable audit trail — one record per field update received.
    Every input (auto-applied OR queued) is logged here.
    """

    __tablename__ = "event_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    activity_fk = Column(Integer, ForeignKey("schedule_activity.id"), nullable=True)

    # Raw input
    raw_input = Column(Text, nullable=False)
    source_file = Column(String(500), nullable=True)
    evidence_type = Column(String(30), nullable=False, default="text")

    # LLM-extracted payload (stored as JSON string)
    extracted_json = Column(Text, nullable=True)

    # Linking results
    matched_activity_id = Column(String(50), nullable=True)
    semantic_score = Column(Float, nullable=True)
    evidence_weight = Column(Float, nullable=True)
    temporal_score = Column(Float, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # Routing outcome
    auto_applied = Column(Boolean, default=False)
    sent_to_review = Column(Boolean, default=False)

    # Provenance
    llm_model_used = Column(String(100), nullable=True)
    timestamp = Column(DateTime, server_default=func.now())

    # Relationships
    activity = relationship("ScheduleActivity", back_populates="event_logs")
    review_item = relationship(
        "ReviewQueueItem", back_populates="event", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def extracted(self) -> dict:
        return json.loads(self.extracted_json) if self.extracted_json else {}

    def __repr__(self) -> str:
        return f"<EventLog id={self.id} conf={self.confidence_score:.2f} auto={self.auto_applied}>"


class ReviewQueueItem(Base):
    """
    Low-confidence or contradictory events parked for planner review.
    Planner can: APPROVE (apply as-is), REJECT (discard), or REMAP (link to different activity).
    """

    __tablename__ = "review_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_log_fk = Column(Integer, ForeignKey("event_log.id"), nullable=False, unique=True)

    status = Column(String(20), nullable=False, default="PENDING")
    # PENDING | APPROVED | REJECTED | REMAPPED

    # Planner override
    remapped_activity_id = Column(String(50), nullable=True)
    planner_notes = Column(Text, nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    event = relationship("EventLog", back_populates="review_item")

    def __repr__(self) -> str:
        return f"<ReviewQueueItem id={self.id} status={self.status}>"
