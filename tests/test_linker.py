"""
SiteSync AI — Tests: Fuzzy Schedule Linker

Tests that field jargon correctly matches formal schedule descriptions.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


@pytest.fixture(scope="module")
def seeded_db(tmp_path_factory):
    """Create a minimal in-memory test DB with known activities."""
    import pickle
    import numpy as np
    from sitesync.linking.embedder import embed_texts

    descriptions = [
        "Erect and weld Line 24-HO-101 spool assembly",
        "Excavation for RCC foundation at Grid A1-B3",
        "MCC-04 Motor Control Centre installation and alignment",
        "Loop check and calibration FT-2401 flow transmitter loop",
        "Hydrostatic pressure test Line 24-HO-101",
    ]
    activity_ids = ["PIP-002", "CIV-001", "ELE-001", "INS-003", "PIP-003"]
    disciplines = ["Piping", "Civil", "Electrical", "Instrumentation", "Piping"]
    planned_starts = ["2024-02-11", "2024-01-15", "2024-01-10", "2024-02-21", "2024-02-26"]
    planned_ends = ["2024-02-25", "2024-01-25", "2024-01-25", "2024-02-28", "2024-02-28"]

    embeddings = embed_texts(descriptions)

    # Use a temp SQLite DB
    import os
    os.environ["DATABASE_URL"] = "sqlite:///./data/test_sitesync.db"

    from sitesync.db.models import ScheduleActivity
    from sitesync.db.session import get_db

    with get_db() as db:
        db.query(ScheduleActivity).delete()
        for i, (desc, aid, disc, ps, pe) in enumerate(
            zip(descriptions, activity_ids, disciplines, planned_starts, planned_ends)
        ):
            act = ScheduleActivity(
                activity_id=aid,
                discipline=disc,
                description=desc,
                planned_start=ps,
                planned_end=pe,
                progress_pct=0.0,
                embedding=pickle.dumps(embeddings[i].astype(np.float32)),
            )
            db.add(act)

    return activity_ids


class TestFuzzyLinker:
    """Test cases for the schedule-linking matcher."""

    def test_spool_erected_matches_pip002(self, seeded_db):
        """'spool erected on 6 inch line' should match PIP-002 (Erect and weld spool)."""
        from sitesync.extraction.schemas import ActivityUpdate
        from sitesync.linking.matcher import ScheduleMatcher

        matcher = ScheduleMatcher()
        matcher.refresh()

        update = ActivityUpdate(
            discipline="Piping",
            location="Tank Farm Area",
            activity_description="spool erected on 6 inch hot oil line",
            actual_progress_pct=32.0,
            date="2024-02-14",
            evidence_type="text",
        )
        result = matcher.match(update, top_k=3)

        assert result.best_match is not None, "Should find a match"
        assert result.best_match.activity_id == "PIP-002", \
            f"Expected PIP-002 but got {result.best_match.activity_id}"
        assert result.best_match.semantic_score >= 0.50, \
            f"Semantic score too low: {result.best_match.semantic_score}"

    def test_rcc_pour_matches_civ001(self, seeded_db):
        """'concrete pour at grid B3' should match CIV-001 (Excavation/foundation)."""
        from sitesync.extraction.schemas import ActivityUpdate
        from sitesync.linking.matcher import ScheduleMatcher

        matcher = ScheduleMatcher()
        matcher.refresh()

        update = ActivityUpdate(
            discipline="Civil",
            location="Tank Farm Area",
            activity_description="RCC footing concrete pour at grid B3 done",
            actual_progress_pct=85.0,
            date="2024-02-14",
            evidence_type="text",
        )
        result = matcher.match(update, top_k=3)
        assert result.best_match is not None
        # Should be a Civil activity
        assert result.best_match.discipline == "Civil"

    def test_mcc_loop_check_matches_instrumentation(self, seeded_db):
        """'E&I loop check on MCC-04' should match INS-003 or ELE-001."""
        from sitesync.extraction.schemas import ActivityUpdate
        from sitesync.linking.matcher import ScheduleMatcher

        matcher = ScheduleMatcher()
        matcher.refresh()

        update = ActivityUpdate(
            discipline="Instrumentation",
            location="DCS Room",
            activity_description="loop check on MCC-04 complete",
            actual_progress_pct=100.0,
            date="2024-03-10",
            evidence_type="text",
        )
        result = matcher.match(update, top_k=3)
        assert result.best_match is not None
        # Top match should be INS or ELE
        assert result.best_match.discipline in ("Instrumentation", "Electrical")

    def test_confidence_formula_weights(self, seeded_db):
        """Verify the multi-signal confidence formula applies correct weights."""
        from sitesync.linking.confidence import compute_confidence

        # Within planned window, spreadsheet evidence
        conf, sem, ev, temp = compute_confidence(
            semantic_score=0.90,
            evidence_type="spreadsheet",
            report_date="2024-02-15",
            planned_start="2024-02-11",
            planned_end="2024-02-25",
        )
        expected = (0.6 * 0.90) + (0.25 * 0.85) + (0.15 * 1.0)
        assert abs(conf - expected) < 0.01, f"Formula mismatch: {conf} vs {expected}"

    def test_high_confidence_above_threshold(self, seeded_db):
        """A high semantic match should produce confidence >= 0.85."""
        from sitesync.extraction.schemas import ActivityUpdate
        from sitesync.linking.matcher import ScheduleMatcher

        matcher = ScheduleMatcher()
        matcher.refresh()

        # Very explicit match
        update = ActivityUpdate(
            discipline="Piping",
            location="Tank Farm",
            activity_description="Erect and weld spool assembly Line 24-HO-101",
            actual_progress_pct=75.0,
            date="2024-02-15",
            evidence_type="spreadsheet",
        )
        result = matcher.match(update)
        assert result.best_match is not None
        assert result.best_match.confidence >= 0.85, \
            f"Expected high confidence but got {result.best_match.confidence}"

    def test_no_match_for_gibberish(self, seeded_db):
        """Gibberish input should return a very low confidence."""
        from sitesync.extraction.schemas import ActivityUpdate
        from sitesync.linking.matcher import ScheduleMatcher

        matcher = ScheduleMatcher()
        matcher.refresh()

        update = ActivityUpdate(
            discipline="Civil",
            location="Unknown",
            activity_description="xyzzy frobnicator quux baz 999",
            actual_progress_pct=50.0,
            date="2024-01-01",
            evidence_type="text",
        )
        result = matcher.match(update)
        if result.best_match:
            assert result.best_match.confidence < 0.85, "Gibberish should not auto-apply"
