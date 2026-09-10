"""SiteSync AI — Linking package."""
from sitesync.linking.embedder import embed_text, deserialize, serialize
from sitesync.linking.confidence import compute_confidence, compute_temporal_score
from sitesync.linking.matcher import MatchResult, LinkingResult, ScheduleMatcher, get_matcher, match

__all__ = [
    "embed_text", "embed_texts", "deserialize", "serialize",
    "compute_confidence", "compute_temporal_score",
    "MatchResult", "LinkingResult", "ScheduleMatcher", "get_matcher", "match",
]
