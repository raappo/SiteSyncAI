"""
End-to-end integration tests for the full pipeline.
Extract → Link → Route → Memory
All tests use in-memory SQLite and tmp ChromaDB.
"""
import pytest
import os

class TestFullPipeline:
    """Integration tests for the complete pipeline."""

    @pytest.fixture(autouse=True)
    def setup_pipeline(self, seeded_db, monkeypatch, tmp_path):
        """Set up a full in-memory pipeline."""
        from sqlalchemy.orm import sessionmaker
        from contextlib import contextmanager
        
        Session = sessionmaker(bind=seeded_db)
        
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
        
        # Override chroma dir
        chroma_dir = str(tmp_path / "test_chroma")
        monkeypatch.setattr("sitesync.config.settings.chroma_persist_dir", chroma_dir)
        
        self.Session = Session

    def test_text_input_full_pipeline(self):
        """Free text input should go through full pipeline without crashing."""
        from sitesync.extraction.extractor import LLMExtractor
        from sitesync.linking.matcher import ScheduleMatcher
        from sitesync.db.models import ScheduleActivity
        from sitesync.linking.embedder import deserialize
        from sitesync.routing.router import route
        import numpy as np
        
        # Extract (offline mock)
        extractor = LLMExtractor()
        result = extractor.extract(
            "Piping team welded 40% of 6-inch hot oil line spools at Tank Farm today, 2026-09-10."
        )
        assert result is not None
        assert len(result.updates) > 0
        
        # Load matcher with seeded activities
        session = self.Session()
        activities = session.query(ScheduleActivity).all()
        vecs = np.stack([deserialize(a.embedding) for a in activities])
        session.expunge_all()
        session.close()
        
        matcher = ScheduleMatcher()
        matcher._activities = activities
        matcher._matrix = vecs.astype(np.float32)
        matcher._loaded = True
        
        # Link
        for update in result.updates:
            linking = matcher.match(update, top_k=3)
            # Route
            event = route(linking)
            assert event is not None
            assert event.id is not None

    def test_multiple_updates_all_routed(self):
        """Multiple updates should all be routed (auto-apply or review queue)."""
        from sitesync.extraction.schemas import ActivityUpdate, ExtractionResult
        from sitesync.linking.matcher import ScheduleMatcher
        from sitesync.db.models import ScheduleActivity, EventLog
        from sitesync.linking.embedder import deserialize
        from sitesync.routing.router import route
        import numpy as np
        
        updates = [
            ActivityUpdate(discipline="Civil", location="Zone A", activity_description="Excavation at column footings Zone A", actual_progress_pct=60.0, date="2026-09-10", evidence_type="text"),
            ActivityUpdate(discipline="Piping", location="Tank Farm", activity_description="Hot oil line spool welding tank farm", actual_progress_pct=45.0, date="2026-09-10", evidence_type="spreadsheet"),
        ]
        
        session = self.Session()
        activities = session.query(ScheduleActivity).all()
        vecs = np.stack([deserialize(a.embedding) for a in activities])
        session.expunge_all()
        session.close()
        
        matcher = ScheduleMatcher()
        matcher._activities = activities
        matcher._matrix = vecs.astype(np.float32)
        matcher._loaded = True
        
        events = []
        for update in updates:
            linking = matcher.match(update, top_k=3)
            event = route(linking)
            events.append(event)
        
        assert len(events) == 2
        assert all(e.id is not None for e in events)

    def test_unmatched_activity_goes_to_review(self):
        """Activity with no schedule match should go to review queue."""
        from sitesync.extraction.schemas import ActivityUpdate
        from sitesync.linking.matcher import LinkingResult
        from sitesync.routing.router import route
        from sitesync.db.models import ReviewQueueItem
        
        update = ActivityUpdate(
            discipline="Civil",
            location="Unknown Zone 99",
            activity_description="Some completely unrelated and unmatchable task xyz",
            actual_progress_pct=10.0,
            date="2026-09-10",
            evidence_type="text",
        )
        unmatched = LinkingResult(update=update, top_matches=[], best_match=None, is_unmatched=True)
        event = route(unmatched)
        
        assert event.sent_to_review is True
        session = self.Session()
        items = session.query(ReviewQueueItem).filter_by(event_log_fk=event.id).all()
        assert len(items) == 1
        assert items[0].status == "PENDING"
        session.close()
