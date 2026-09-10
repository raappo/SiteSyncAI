"""
Tests for the hybrid matching module (raptor_match.py):
  - _expand_abbreviations()
  - hybrid_match() — with and without RapidFuzz
"""
import pytest
import numpy as np
from sqlalchemy.orm import sessionmaker


class TestExpandAbbreviations:
    """Tests for the construction abbreviation expander."""

    def test_known_abbreviation_expands(self):
        from sitesync.linking.raptor_match import _expand_abbreviations
        result = _expand_abbreviations("rcc footing")
        assert "reinforced cement concrete" in result

    def test_multiple_abbreviations_expand(self):
        from sitesync.linking.raptor_match import _expand_abbreviations
        result = _expand_abbreviations("ms pipe cs spool")
        assert "mild steel" in result
        assert "carbon steel" in result

    def test_unknown_words_passthrough(self):
        from sitesync.linking.raptor_match import _expand_abbreviations
        result = _expand_abbreviations("welding excavation")
        assert "welding" in result
        assert "excavation" in result

    def test_case_insensitive(self):
        from sitesync.linking.raptor_match import _expand_abbreviations
        result = _expand_abbreviations("RCC FOOTING")
        assert "reinforced cement concrete" in result

    def test_empty_string_returns_empty(self):
        from sitesync.linking.raptor_match import _expand_abbreviations
        result = _expand_abbreviations("")
        assert result == ""

    def test_piping_abbrev_expands(self):
        from sitesync.linking.raptor_match import _expand_abbreviations
        result = _expand_abbreviations("spool erection")
        assert "prefabricated pipe spool" in result


class TestHybridMatch:
    """Tests for hybrid_match() using in-memory DB."""

    @pytest.fixture(autouse=True)
    def _load_matcher(self, seeded_db):
        """Prepare a ScheduleMatcher loaded from the seeded in-memory DB."""
        from sitesync.linking.matcher import ScheduleMatcher
        from sitesync.db.models import ScheduleActivity
        from sitesync.linking.embedder import deserialize

        Session = sessionmaker(bind=seeded_db)
        session = Session()
        activities = session.query(ScheduleActivity).all()
        vecs = np.stack([deserialize(a.embedding) for a in activities])
        session.expunge_all()
        session.close()

        self.matcher = ScheduleMatcher()
        self.matcher._activities = activities
        self.matcher._matrix = vecs.astype(np.float32)
        self.matcher._loaded = True

    def test_hybrid_match_returns_linking_result(self, monkeypatch):
        """hybrid_match should return a LinkingResult."""
        from sitesync.linking.raptor_match import hybrid_match
        from sitesync.extraction.schemas import ActivityUpdate
        from sitesync.linking.matcher import LinkingResult

        monkeypatch.setattr("sitesync.linking.raptor_match.get_matcher", lambda: self.matcher)

        update = ActivityUpdate(
            discipline="Piping",
            location="Tank Farm",
            activity_description="Welding spools on hot oil line",
            actual_progress_pct=35.0,
            date="2026-09-10",
            evidence_type="text",
        )
        result = hybrid_match(update, top_k=3)
        assert isinstance(result, LinkingResult)
        assert result.best_match is not None

    def test_hybrid_match_piping_query(self, monkeypatch):
        """Piping query should match the piping schedule activity."""
        from sitesync.linking.raptor_match import hybrid_match
        from sitesync.extraction.schemas import ActivityUpdate

        monkeypatch.setattr("sitesync.linking.raptor_match.get_matcher", lambda: self.matcher)

        update = ActivityUpdate(
            discipline="Piping",
            location="Tank Farm",
            activity_description="Erect and weld spools on 6-inch hot oil line",
            actual_progress_pct=40.0,
            date="2026-09-10",
            evidence_type="spreadsheet",
        )
        result = hybrid_match(update, top_k=3)
        assert result.best_match is not None
        assert result.best_match.activity_id == "PIPING-001"

    def test_hybrid_match_confidence_in_range(self, monkeypatch):
        """Confidence scores should always be in [0, 1]."""
        from sitesync.linking.raptor_match import hybrid_match
        from sitesync.extraction.schemas import ActivityUpdate

        monkeypatch.setattr("sitesync.linking.raptor_match.get_matcher", lambda: self.matcher)

        update = ActivityUpdate(
            discipline="Civil",
            location="Zone A",
            activity_description="Excavation for column footings",
            actual_progress_pct=50.0,
            date="2026-09-10",
            evidence_type="text",
        )
        result = hybrid_match(update, top_k=3)
        for match in result.top_matches:
            assert 0.0 <= match.confidence <= 1.0

    def test_hybrid_match_top_k_respects_limit(self, monkeypatch):
        """Returned matches should not exceed top_k."""
        from sitesync.linking.raptor_match import hybrid_match
        from sitesync.extraction.schemas import ActivityUpdate

        monkeypatch.setattr("sitesync.linking.raptor_match.get_matcher", lambda: self.matcher)

        update = ActivityUpdate(
            discipline="Electrical",
            location="Unit 1",
            activity_description="Install cable trays and conduits",
            actual_progress_pct=20.0,
            date="2026-09-10",
            evidence_type="text",
        )
        result = hybrid_match(update, top_k=2)
        assert len(result.top_matches) <= 2

    def test_hybrid_match_sorted_by_confidence(self, monkeypatch):
        """Top matches should be sorted by confidence descending."""
        from sitesync.linking.raptor_match import hybrid_match
        from sitesync.extraction.schemas import ActivityUpdate

        monkeypatch.setattr("sitesync.linking.raptor_match.get_matcher", lambda: self.matcher)

        update = ActivityUpdate(
            discipline="Piping",
            location="Tank Farm",
            activity_description="Hot oil piping spool weld",
            actual_progress_pct=30.0,
            date="2026-09-10",
            evidence_type="text",
        )
        result = hybrid_match(update, top_k=3)
        confs = [m.confidence for m in result.top_matches]
        assert confs == sorted(confs, reverse=True), "Matches should be sorted by confidence (desc)"

    def test_hybrid_match_empty_schedule_returns_unmatched(self, monkeypatch):
        """If matcher has no activities, result should be unmatched."""
        from sitesync.linking.raptor_match import hybrid_match
        from sitesync.linking.matcher import ScheduleMatcher
        from sitesync.extraction.schemas import ActivityUpdate

        empty_matcher = ScheduleMatcher()
        empty_matcher._activities = []
        empty_matcher._matrix = None
        empty_matcher._loaded = True

        monkeypatch.setattr("sitesync.linking.raptor_match.get_matcher", lambda: empty_matcher)

        update = ActivityUpdate(
            discipline="Civil",
            location="Zone A",
            activity_description="Excavation works",
            actual_progress_pct=50.0,
            date="2026-09-10",
            evidence_type="text",
        )
        result = hybrid_match(update)
        assert result.is_unmatched is True
