"""
Tests for the schedule-linking (matcher + confidence) modules.
All tests use in-memory SQLite — safe to run alongside production data.
"""
import pytest
import numpy as np
from sqlalchemy.orm import sessionmaker

class TestComputeConfidence:
    """Tests for confidence scoring formula."""

    def test_high_semantic_high_evidence_gives_high_confidence(self):
        from sitesync.linking.confidence import compute_confidence
        conf, s, e, t = compute_confidence(
            semantic_score=0.92,
            evidence_type="spreadsheet",
            report_date="2026-06-15",
            planned_start="2026-05-01",
            planned_end="2026-08-01",
        )
        assert conf >= 0.80, f"Expected high confidence, got {conf}"
        assert s == pytest.approx(0.92)

    def test_low_semantic_gives_low_confidence(self):
        from sitesync.linking.confidence import compute_confidence
        conf, s, e, t = compute_confidence(
            semantic_score=0.20,
            evidence_type="text",
            report_date="2026-06-15",
            planned_start="2026-05-01",
            planned_end="2026-08-01",
        )
        assert conf < 0.50

    def test_evidence_type_text_lower_than_spreadsheet(self):
        from sitesync.linking.confidence import compute_confidence
        conf_text, _, e_text, _ = compute_confidence(
            semantic_score=0.75, evidence_type="text",
            report_date=None, planned_start=None, planned_end=None
        )
        conf_sheet, _, e_sheet, _ = compute_confidence(
            semantic_score=0.75, evidence_type="spreadsheet",
            report_date=None, planned_start=None, planned_end=None
        )
        assert e_text < e_sheet, "Spreadsheet evidence should weigh more than text"
        assert conf_text < conf_sheet

    def test_missing_dates_uses_neutral_temporal(self):
        from sitesync.linking.confidence import compute_confidence
        _, _, _, temporal = compute_confidence(
            semantic_score=0.75, evidence_type="text",
            report_date=None, planned_start=None, planned_end=None
        )
        assert temporal == pytest.approx(0.5)

    def test_date_within_window_gives_full_temporal(self):
        from sitesync.linking.confidence import compute_confidence
        _, _, _, temporal = compute_confidence(
            semantic_score=0.75, evidence_type="text",
            report_date="2026-06-15",
            planned_start="2026-05-01",
            planned_end="2026-08-01",
        )
        assert temporal == pytest.approx(1.0)

    def test_date_far_outside_window_gives_low_temporal(self):
        from sitesync.linking.confidence import compute_confidence
        _, _, _, temporal = compute_confidence(
            semantic_score=0.75, evidence_type="text",
            report_date="2024-01-01",  # Far in the past
            planned_start="2026-05-01",
            planned_end="2026-08-01",
        )
        assert temporal < 0.5

class TestScheduleMatcher:
    """Tests for ScheduleMatcher using in-memory DB."""

    def test_match_returns_top_k_results(self, seeded_db):
        """Matching should return up to top_k results."""
        from sitesync.linking.matcher import ScheduleMatcher
        from sitesync.extraction.schemas import ActivityUpdate
        from sqlalchemy.orm import sessionmaker
        
        matcher = ScheduleMatcher()
        # Override the session to use in-memory DB
        from sitesync.db import models
        from sitesync.db.session import get_db
        
        # Load activities manually into matcher
        Session = sessionmaker(bind=seeded_db)
        session = Session()
        from sitesync.db.models import ScheduleActivity
        activities = session.query(ScheduleActivity).all()
        
        from sitesync.linking.embedder import deserialize
        import numpy as np
        vecs = np.stack([deserialize(a.embedding) for a in activities])
        matcher._activities = activities
        matcher._matrix = vecs.astype(np.float32)
        matcher._loaded = True
        session.expunge_all()
        session.close()
        
        update = ActivityUpdate(
            discipline="Piping",
            location="Tank Farm",
            activity_description="Welding spools on hot oil line",
            actual_progress_pct=35.0,
            date="2026-09-10",
            evidence_type="text",
        )
        result = matcher.match(update, top_k=3)
        assert len(result.top_matches) <= 3
        assert result.best_match is not None

    def test_piping_query_matches_piping_activity(self, seeded_db):
        """Piping-related query should match the piping schedule activity."""
        from sitesync.linking.matcher import ScheduleMatcher
        from sitesync.extraction.schemas import ActivityUpdate
        from sitesync.db.models import ScheduleActivity
        from sitesync.linking.embedder import deserialize
        from sqlalchemy.orm import sessionmaker
        import numpy as np
        
        Session = sessionmaker(bind=seeded_db)
        session = Session()
        activities = session.query(ScheduleActivity).all()
        vecs = np.stack([deserialize(a.embedding) for a in activities])
        
        matcher = ScheduleMatcher()
        matcher._activities = activities
        matcher._matrix = vecs.astype(np.float32)
        matcher._loaded = True
        session.expunge_all()
        session.close()
        
        update = ActivityUpdate(
            discipline="Piping",
            location="Tank Farm",
            activity_description="Welding 6-inch hot oil line spools at tank farm",
            actual_progress_pct=40.0,
            date="2026-09-10",
            evidence_type="text",
        )
        result = matcher.match(update, top_k=3)
        assert result.best_match is not None
        assert result.best_match.activity_id == "PIPING-001"

    def test_no_activities_returns_unmatched(self):
        """Matcher with empty matrix should return is_unmatched=True."""
        from sitesync.linking.matcher import ScheduleMatcher
        from sitesync.extraction.schemas import ActivityUpdate
        import numpy as np
        
        matcher = ScheduleMatcher()
        matcher._activities = []
        matcher._matrix = None
        matcher._loaded = True
        
        update = ActivityUpdate(
            discipline="Civil",
            location="Zone A",
            activity_description="Excavation works",
            actual_progress_pct=50.0,
            date="2026-09-10",
            evidence_type="text",
        )
        result = matcher.match(update)
        assert result.is_unmatched is True
        assert result.error is not None
