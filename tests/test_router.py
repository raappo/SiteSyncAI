"""
Tests for the routing engine.
All tests use in-memory SQLite for isolation.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestDetectContradiction:
    """Tests for the contradiction detection helper."""

    def test_no_contradiction_when_progress_increases(self):
        from sitesync.routing.router import _detect_contradiction
        from sitesync.db.models import ScheduleActivity
        activity = ScheduleActivity(activity_id="TEST", discipline="Civil", description="test", progress_pct=50.0)
        assert _detect_contradiction(activity, 75.0) is False

    def test_no_contradiction_when_same_progress(self):
        from sitesync.routing.router import _detect_contradiction
        from sitesync.db.models import ScheduleActivity
        activity = ScheduleActivity(activity_id="TEST", discipline="Civil", description="test", progress_pct=50.0)
        assert _detect_contradiction(activity, 50.0) is False

    def test_contradiction_when_progress_drops_significantly(self):
        from sitesync.routing.router import _detect_contradiction
        from sitesync.db.models import ScheduleActivity
        activity = ScheduleActivity(activity_id="TEST", discipline="Civil", description="test", progress_pct=60.0)
        assert _detect_contradiction(activity, 40.0) is True  # 60 - 40 = 20 > 10

    def test_no_contradiction_within_10pp_threshold(self):
        from sitesync.routing.router import _detect_contradiction
        from sitesync.db.models import ScheduleActivity
        activity = ScheduleActivity(activity_id="TEST", discipline="Civil", description="test", progress_pct=55.0)
        assert _detect_contradiction(activity, 48.0) is False  # 55 - 48 = 7 < 10

    def test_no_contradiction_when_no_current_progress(self):
        from sitesync.routing.router import _detect_contradiction
        from sitesync.db.models import ScheduleActivity
        activity = ScheduleActivity(activity_id="TEST", discipline="Civil", description="test", progress_pct=None)
        assert _detect_contradiction(activity, 10.0) is False

class TestRouter:
    """Tests for the route() function with in-memory DB."""

    @pytest.fixture(autouse=True)
    def setup_db(self, in_memory_engine, monkeypatch):
        """Patch get_db to use in-memory engine."""
        from sitesync.db.models import Base, ScheduleActivity
        from sitesync.linking.embedder import serialize, embed_text_passage
        from sqlalchemy.orm import sessionmaker
        from contextlib import contextmanager

        Session = sessionmaker(bind=in_memory_engine)
        
        @contextmanager
        def mock_get_db():
            session = Session()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        
        monkeypatch.setattr("sitesync.routing.router.get_db", mock_get_db)
        
        # Insert a test activity
        session = Session()
        activity = ScheduleActivity(
            activity_id="CIVIL-TEST",
            discipline="Civil",
            description="Excavation for column footing",
            location="Zone A",
            planned_start="2026-01-01",
            planned_end="2026-12-31",
            progress_pct=20.0,
            embedding=serialize(embed_text_passage("Excavation for column footing")),
        )
        session.add(activity)
        session.commit()
        session.close()
        
        self.Session = Session

    def _make_linking_result(self, confidence: float, activity_id: str = "CIVIL-TEST", progress: float = 50.0):
        """Helper to build a LinkingResult for testing."""
        from sitesync.extraction.schemas import ActivityUpdate
        from sitesync.linking.matcher import LinkingResult, MatchResult
        
        update = ActivityUpdate(
            discipline="Civil",
            location="Zone A",
            activity_description="Excavation works",
            actual_progress_pct=progress,
            date="2026-09-10",
            evidence_type="text",
        )
        match = MatchResult(
            activity_id=activity_id,
            description="Excavation for column footing",
            discipline="Civil",
            location="Zone A",
            planned_start="2026-01-01",
            planned_end="2026-12-31",
            wbs_code=None,
            semantic_score=confidence,
            evidence_weight=0.60,
            temporal_score=1.0,
            confidence=confidence,
            rank=1,
        )
        return LinkingResult(update=update, top_matches=[match], best_match=match, is_unmatched=False)

    def test_high_confidence_auto_applies(self):
        """High confidence (>=0.85) should auto-apply the update."""
        from sitesync.routing.router import route
        from sitesync.db.models import EventLog
        
        result = self._make_linking_result(confidence=0.90)
        event = route(result)
        
        assert event.auto_applied is True
        assert event.sent_to_review is False
        
        # Verify schedule was updated
        session = self.Session()
        from sitesync.db.models import ScheduleActivity
        act = session.query(ScheduleActivity).filter_by(activity_id="CIVIL-TEST").first()
        assert act.progress_pct == 50.0  # Updated from 20 to 50
        session.close()

    def test_low_confidence_goes_to_review(self):
        """Low confidence (<0.85) should create a review queue item."""
        from sitesync.routing.router import route
        from sitesync.db.models import ReviewQueueItem
        
        result = self._make_linking_result(confidence=0.60)
        event = route(result)
        
        assert event.sent_to_review is True
        assert event.auto_applied is False
        
        session = self.Session()
        item = session.query(ReviewQueueItem).filter_by(event_log_fk=event.id).first()
        assert item is not None
        assert item.status == "PENDING"
        session.close()

    def test_no_match_goes_to_review(self):
        """No match should always create a review queue item."""
        from sitesync.routing.router import route
        from sitesync.extraction.schemas import ActivityUpdate
        from sitesync.linking.matcher import LinkingResult
        
        update = ActivityUpdate(
            discipline="Civil",
            location="Unknown",
            activity_description="Some unknown activity",
            actual_progress_pct=50.0,
            date="2026-09-10",
            evidence_type="text",
        )
        no_match_result = LinkingResult(update=update, top_matches=[], best_match=None, is_unmatched=True)
        event = route(no_match_result)
        
        assert event.sent_to_review is True

    def test_contradiction_goes_to_review(self):
        """Progress contradiction should route to review even with high confidence."""
        from sitesync.routing.router import route
        from sitesync.db.models import ReviewQueueItem
        
        # Activity has 20% progress, new update says 5% (contradiction!)
        result = self._make_linking_result(confidence=0.92, progress=5.0)
        event = route(result)
        
        # Should go to review due to contradiction
        assert event.sent_to_review is True
        
        session = self.Session()
        item = session.query(ReviewQueueItem).filter_by(event_log_fk=event.id).first()
        assert item is not None
        assert "Contradiction" in (item.planner_notes or "")
        session.close()

    def test_progress_never_regresses_on_auto_apply(self):
        """Auto-apply should use max() — never regress progress."""
        from sitesync.routing.router import route
        from sitesync.db.models import ScheduleActivity
        
        # Activity has 20%, new update says 15% (small diff, no contradiction), but high confidence
        result = self._make_linking_result(confidence=0.92, progress=15.0)
        # With 20% current and 15% new, difference is 5pp which is within contradiction threshold (10pp)
        # So it won't contradict, but max() should keep it at 20%
        event = route(result)
        
        session = self.Session()
        act = session.query(ScheduleActivity).filter_by(activity_id="CIVIL-TEST").first()
        assert act.progress_pct >= 20.0  # Should not regress
        session.close()
