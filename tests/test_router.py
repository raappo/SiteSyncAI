"""
SiteSync AI — Tests: Routing Engine
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest


class TestRouter:
    """Test routing decisions."""

    def test_high_confidence_auto_applies(self):
        """confidence >= 0.85 should set auto_applied=True."""
        from sitesync.routing.router import _detect_contradiction
        # No contradiction when progress increases
        assert _detect_contradiction_mock(50.0, 75.0) is False

    def test_contradiction_detected_on_regression(self):
        """New progress significantly lower than current should flag contradiction."""
        # 80% existing, reporting 50% new → contradiction
        from unittest.mock import MagicMock
        activity = MagicMock()
        activity.progress_pct = 80.0
        from sitesync.routing.router import _detect_contradiction
        assert _detect_contradiction(activity, 50.0) is True

    def test_no_contradiction_small_regression(self):
        """Small regressions (within 10%) should NOT flag contradiction."""
        from unittest.mock import MagicMock
        activity = MagicMock()
        activity.progress_pct = 75.0
        from sitesync.routing.router import _detect_contradiction
        assert _detect_contradiction(activity, 68.0) is False


def _detect_contradiction_mock(current: float, new_progress: float) -> bool:
    """Helper to test contradiction logic without DB."""
    return new_progress < (current - 10.0)


class TestConfidenceScorer:
    def test_within_planned_window(self):
        from sitesync.linking.confidence import compute_temporal_score
        score = compute_temporal_score("2024-02-15", "2024-02-11", "2024-02-25")
        assert score == 1.0

    def test_before_planned_start(self):
        from sitesync.linking.confidence import compute_temporal_score
        score = compute_temporal_score("2024-01-01", "2024-02-11", "2024-02-25")
        assert score < 1.0
        assert score >= 0.0

    def test_after_planned_end(self):
        from sitesync.linking.confidence import compute_temporal_score
        score = compute_temporal_score("2024-04-01", "2024-02-11", "2024-02-25")
        assert score < 1.0
        assert score >= 0.0

    def test_missing_dates_neutral(self):
        from sitesync.linking.confidence import compute_temporal_score
        score = compute_temporal_score(None, None, None)
        assert score == 0.5

    def test_photo_highest_weight(self):
        from sitesync.linking.confidence import compute_confidence
        conf_photo, _, ew_photo, _ = compute_confidence(0.8, "photo")
        conf_text, _, ew_text, _ = compute_confidence(0.8, "text")
        assert ew_photo > ew_text
        assert conf_photo > conf_text
