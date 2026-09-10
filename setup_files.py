import os
from pathlib import Path

files = {}

files["tests/conftest.py"] = '''"""
Shared pytest fixtures for SiteSync AI tests.
All DB fixtures use in-memory SQLite — never touch the production DB.
"""
import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

@pytest.fixture(scope="session", autouse=True)
def override_env_before_imports(tmp_path_factory):
    """Override env vars before any sitesync imports happen."""
    tmp_dir = tmp_path_factory.mktemp("sitesync_test")
    db_url = "sqlite:///:memory:"
    chroma_dir = str(tmp_dir / "chroma")
    os.environ["DATABASE_URL"] = db_url
    os.environ["CHROMA_PERSIST_DIR"] = chroma_dir
    os.environ["NVIDIA_API_KEY"] = ""
    os.environ["EXPLABS_API_KEY"] = ""
    os.environ["AZURE_DOCUMENT_INTELLIGENCE_KEY"] = ""
    os.environ["AZURE_OPENAI_API_KEY"] = ""
    yield

@pytest.fixture(scope="function")
def in_memory_engine():
    """Create a fresh in-memory SQLite engine with all tables."""
    from sitesync.db.models import Base
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()

@pytest.fixture(scope="function")
def db_session(in_memory_engine):
    """Create a fresh DB session backed by in-memory SQLite."""
    Session = sessionmaker(bind=in_memory_engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture(scope="function")
def seeded_db(in_memory_engine):
    """Seed the in-memory DB with 5 known schedule activities."""
    from sitesync.db.models import Base, ScheduleActivity
    from sitesync.linking.embedder import embed_text_passage, serialize
    
    Session = sessionmaker(bind=in_memory_engine)
    session = Session()
    
    activities = [
        ScheduleActivity(
            activity_id="CIVIL-001",
            discipline="Civil",
            description="Excavation for column footing Zone A",
            location="Zone A",
            planned_start="2026-01-01",
            planned_end="2026-03-31",
            progress_pct=0.0,
            embedding=serialize(embed_text_passage("Excavation for column footing Zone A")),
        ),
        ScheduleActivity(
            activity_id="PIPING-001",
            discipline="Piping",
            description="Erect and weld spools on 6-inch hot oil line",
            location="Tank Farm",
            planned_start="2026-01-15",
            planned_end="2026-04-15",
            progress_pct=30.0,
            embedding=serialize(embed_text_passage("Erect and weld spools on 6-inch hot oil line")),
        ),
        ScheduleActivity(
            activity_id="ELEC-001",
            discipline="Electrical",
            description="Install cable trays and conduits in Unit 1",
            location="Unit 1",
            planned_start="2026-02-01",
            planned_end="2026-05-01",
            progress_pct=0.0,
            embedding=serialize(embed_text_passage("Install cable trays and conduits in Unit 1")),
        ),
        ScheduleActivity(
            activity_id="INST-001",
            discipline="Instrumentation",
            description="Install transmitters and control loops for Tank T-01",
            location="Tank T-01",
            planned_start="2026-03-01",
            planned_end="2026-06-01",
            progress_pct=0.0,
            embedding=serialize(embed_text_passage("Install transmitters and control loops for Tank T-01")),
        ),
        ScheduleActivity(
            activity_id="HSE-001",
            discipline="HSE",
            description="HSE safety audit and tool box talks Zone B",
            location="Zone B",
            planned_start="2026-01-01",
            planned_end="2026-12-31",
            progress_pct=50.0,
            embedding=serialize(embed_text_passage("HSE safety audit and tool box talks Zone B")),
        ),
    ]
    
    for a in activities:
        session.add(a)
    session.commit()
    yield in_memory_engine
    session.close()

@pytest.fixture(scope="function")
def mock_extractor(monkeypatch):
    """Mock LLM extractor that returns deterministic results."""
    from sitesync.extraction.schemas import ActivityUpdate, ExtractionResult
    
    def _mock_extract(raw_input, evidence_type="text"):
        return ExtractionResult(
            updates=[
                ActivityUpdate(
                    discipline="Piping",
                    location="Tank Farm",
                    activity_description="Welding spools on hot oil line",
                    actual_progress_pct=35.0,
                    date="2026-09-10",
                    evidence_type=evidence_type,
                )
            ],
            raw_llm_response="MOCK",
            model_used="mock",
            extraction_ms=1.0,
        )
    
    monkeypatch.setattr("sitesync.extraction.extractor.extract", _mock_extract)
    return _mock_extract
'''

files["tests/test_linker.py"] = '''"""
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
'''

files["tests/test_router.py"] = '''"""
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
'''

files["tests/test_extractor.py"] = '''"""
Tests for the LLM extraction layer.
Tests run with mock/offline mode (no real API calls).
"""
import pytest
import json

class TestParseJsonArray:
    """Tests for the JSON parsing helper."""

    def _get_extractor(self):
        from sitesync.extraction.extractor import LLMExtractor
        e = LLMExtractor.__new__(LLMExtractor)
        from langchain_core.output_parsers import PydanticOutputParser
        from sitesync.extraction.schemas import ActivityUpdate
        e._parser = PydanticOutputParser(pydantic_object=ActivityUpdate)
        e._clients = []
        return e

    def test_parse_valid_json_array(self):
        from sitesync.extraction.schemas import ActivityUpdate
        e = self._get_extractor()
        data = json.dumps([{
            "discipline": "Piping",
            "location": "Tank Farm",
            "activity_description": "Weld hot oil line spools",
            "actual_progress_pct": 35.0,
            "date": "2026-09-10",
            "evidence_type": "text",
        }])
        results = e._parse_json_array(data, "text")
        assert len(results) == 1
        assert results[0].discipline == "Piping"

    def test_parse_markdown_fenced_json(self):
        e = self._get_extractor()
        data = \'\'\'```json
[{"discipline": "Civil", "location": "Zone A", "activity_description": "Excavation works", "actual_progress_pct": 50.0, "date": "2026-09-10", "evidence_type": "text"}]
```\'\'\'
        results = e._parse_json_array(data, "text")
        assert len(results) == 1
        assert results[0].discipline == "Civil"

    def test_parse_single_object_wraps_in_list(self):
        e = self._get_extractor()
        data = json.dumps({
            "discipline": "Electrical",
            "location": "Unit 1",
            "activity_description": "Cable tray installation",
            "actual_progress_pct": 20.0,
            "date": "2026-09-10",
            "evidence_type": "text",
        })
        results = e._parse_json_array(data, "text")
        assert len(results) == 1

    def test_parse_multiple_updates(self):
        e = self._get_extractor()
        items = [
            {"discipline": "Civil", "location": "A", "activity_description": "Exc", "actual_progress_pct": 10, "date": "2026-09-10", "evidence_type": "text"},
            {"discipline": "Piping", "location": "B", "activity_description": "Weld", "actual_progress_pct": 20, "date": "2026-09-10", "evidence_type": "text"},
        ]
        results = e._parse_json_array(json.dumps(items), "text")
        assert len(results) == 2

    def test_parse_injects_evidence_type_if_missing(self):
        e = self._get_extractor()
        data = json.dumps([{
            "discipline": "Civil",
            "location": "Zone A",
            "activity_description": "Excavation",
            "actual_progress_pct": 50.0,
            "date": "2026-09-10",
            # No evidence_type
        }])
        results = e._parse_json_array(data, "spreadsheet")
        assert results[0].evidence_type == "spreadsheet"

    def test_parse_invalid_json_raises(self):
        e = self._get_extractor()
        with pytest.raises((ValueError, Exception)):
            e._parse_json_array("This is not JSON at all {broken", "text")

class TestMockFallback:
    """Tests that the mock fallback works when no LLM is configured."""

    def test_extract_returns_result_with_no_api_keys(self):
        """With no API keys, extract() should return a mock result without crashing."""
        from sitesync.extraction.extractor import LLMExtractor
        e = LLMExtractor()  # No keys → empty _clients → falls to mock
        result = e.extract("Piping team completed 40% of spools in tank farm today.")
        # Should not raise
        assert result is not None
        assert len(result.updates) >= 1 or result.error is not None

    def test_mock_fallback_uses_today_date(self):
        """Mock fallback should use today's date, not a hardcoded historical date."""
        import datetime
        from sitesync.extraction.extractor import LLMExtractor
        e = LLMExtractor.__new__(LLMExtractor)
        from langchain_core.output_parsers import PydanticOutputParser
        from sitesync.extraction.schemas import ActivityUpdate
        e._parser = PydanticOutputParser(pydantic_object=ActivityUpdate)
        e._clients = []  # Force mock
        
        from langchain_core.messages import HumanMessage
        prompt_value = [HumanMessage(content="Test input")]
        _, updates, model = e._call_with_fallback(prompt_value, "text")
        
        today = datetime.date.today().isoformat()
        assert model == "offline-mock-fallback"
        assert updates[0].date == today, f"Expected today {today}, got {updates[0].date}"
'''

files["tests/test_config.py"] = '''"""
Tests for the configuration module.
"""
import pytest

class TestSettings:
    """Tests for Settings configuration."""

    def test_active_models_empty_when_no_keys(self):
        """With no API keys, active_models should be empty."""
        from sitesync.config import Settings
        s = Settings(
            nvidia_api_key="",
            explabs_api_key="",
        )
        assert s.active_models == []

    def test_has_nvidia_false_when_empty(self):
        from sitesync.config import Settings
        s = Settings(nvidia_api_key="")
        assert s.has_nvidia is False

    def test_has_nvidia_true_when_set(self):
        from sitesync.config import Settings
        s = Settings(nvidia_api_key="test-key-123")
        assert s.has_nvidia is True

    def test_embedding_backend_ngram_when_no_keys(self):
        from sitesync.config import Settings
        s = Settings(nvidia_api_key="", azure_openai_api_key="", azure_openai_endpoint="")
        assert s.embedding_backend == "ngram"

    def test_embedding_backend_nvidia_when_only_nvidia_set(self):
        from sitesync.config import Settings
        s = Settings(nvidia_api_key="test-key", azure_openai_api_key="", azure_openai_endpoint="")
        assert s.embedding_backend == "nvidia"

    def test_embedding_backend_azure_takes_priority(self):
        from sitesync.config import Settings
        s = Settings(
            nvidia_api_key="test-nvidia",
            azure_openai_api_key="test-azure",
            azure_openai_endpoint="https://example.azure.com/",
        )
        assert s.embedding_backend == "azure_openai"

    def test_confidence_threshold_default(self):
        from sitesync.config import Settings
        s = Settings()
        assert s.confidence_threshold == 0.85

    def test_has_azure_di_false_when_incomplete(self):
        from sitesync.config import Settings
        s = Settings(azure_document_intelligence_endpoint="https://example.com", azure_document_intelligence_key="")
        assert s.has_azure_di is False

    def test_active_models_nvidia_only(self):
        from sitesync.config import Settings
        s = Settings(nvidia_api_key="test-key", explabs_api_key="")
        models = s.active_models
        assert len(models) >= 1
        assert any("nvidia" in url or "nvidia" in model_id for url, key, model_id in models)
'''

files["tests/test_doc_parser.py"] = '''"""
Tests for the document parser module.
"""
import pytest
from pathlib import Path

class TestDocParser:
    """Tests for the multimodal document parser."""

    def test_parse_plain_text_passthrough(self, tmp_path):
        """Plain text files should be passed through directly."""
        from sitesync.ingestion.doc_parser import parse_file
        txt_file = tmp_path / "test_report.txt"
        txt_file.write_text("Civil team completed 60% excavation at Zone A today.", encoding="utf-8")
        result = parse_file(str(txt_file))
        assert result.error is None or result.error == ""
        assert "excavation" in result.raw_text.lower()

    def test_parse_xlsx_returns_text(self, tmp_path):
        """Excel files should be parsed into text representation."""
        pytest.importorskip("openpyxl")
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Progress"
        ws.append(["Activity", "Progress", "Date"])
        ws.append(["Piping spool weld", "35%", "2026-09-10"])
        xlsx_path = tmp_path / "test.xlsx"
        wb.save(str(xlsx_path))
        
        from sitesync.ingestion.doc_parser import parse_file
        result = parse_file(str(xlsx_path))
        assert result.raw_text != ""
        assert result.evidence_type == "spreadsheet"

    def test_parse_image_without_azure_di_returns_error(self, tmp_path):
        """Image files without Azure DI should return an error, not crash."""
        # Create a minimal PNG (1x1 pixel)
        img_path = tmp_path / "test.png"
        # Write minimal valid PNG bytes
        import struct, zlib
        def write_png(path):
            sig = b'\\x89PNG\\r\\n\\x1a\\n'
            def chunk(name, data):
                c = struct.pack('>I', len(data)) + name + data
                return c + struct.pack('>I', zlib.crc32(name + data) & 0xffffffff)
            ihdr = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
            raw = b'\\x00\\xff\\xff\\xff'  # 1 pixel, RGB
            idat = zlib.compress(raw)
            path.write_bytes(sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', idat) + chunk(b'IEND', b''))
        write_png(img_path)
        
        from sitesync.ingestion.doc_parser import parse_file
        result = parse_file(str(img_path))
        # Should not crash, should return an error document
        assert result is not None
        # Image without Azure DI should indicate failure gracefully
        assert result.error is not None or result.raw_text == ""

    def test_parse_nonexistent_file_returns_error(self):
        """Nonexistent files should return an error document."""
        from sitesync.ingestion.doc_parser import parse_file
        result = parse_file("/nonexistent/path/file.txt")
        assert result.error is not None
        assert result.raw_text == ""
'''

files["tests/test_pipeline_integration.py"] = '''"""
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
'''

files["scripts/run_all_tests.ps1"] = '''<#
.SYNOPSIS
    SiteSync AI — Full Test Runner
    Runs the complete test suite and shows a summary.
.DESCRIPTION
    1. Seeds the database (in-memory for tests)
    2. Runs all pytest tests with coverage
    3. Reports pass/fail summary
#>

$ErrorActionPreference = "Continue"
$startTime = Get-Date

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  SiteSync AI — Full Test Suite" -ForegroundColor Cyan  
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# Check if uv is available
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "ERROR: 'uv' not found. Install: pip install uv" -ForegroundColor Red
    exit 1
}

# Run tests
Write-Host "Running pytest..." -ForegroundColor Yellow
uv run pytest tests/ -v --tb=short --no-header -q 2>&1 | Tee-Object -Variable testOutput

$exitCode = $LASTEXITCODE
$duration = (Get-Date) - $startTime

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
if ($exitCode -eq 0) {
    Write-Host "  ✅ ALL TESTS PASSED  (Duration: $($duration.TotalSeconds.ToString('F1'))s)" -ForegroundColor Green
} else {
    Write-Host "  ❌ SOME TESTS FAILED  (Duration: $($duration.TotalSeconds.ToString('F1'))s)" -ForegroundColor Red
}
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

exit $exitCode
'''

files["sitesync/analytics/__init__.py"] = ""

files["sitesync/analytics/kpi_engine.py"] = '''"""
SiteSync AI — KPI Engine

Computes project performance KPIs from the schedule database:
- Overall % complete
- Schedule Performance Index (SPI)
- Activities by status (on-track / at-risk / behind)
- Discipline-wise breakdown
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import datetime

from sitesync.db.models import ScheduleActivity
from sitesync.db.session import get_db

@dataclass
class DisciplineKPI:
    discipline: str
    total_activities: int
    avg_progress: float
    on_track: int
    at_risk: int
    behind: int
    completed: int

@dataclass
class KPIReport:
    overall_progress: float
    total_activities: int
    completed_activities: int
    on_track_count: int
    at_risk_count: int
    behind_count: int
    auto_applied_count: int
    pending_review_count: int
    spi: float  # Schedule Performance Index
    disciplines: list[DisciplineKPI] = field(default_factory=list)
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.datetime.now().isoformat()

def compute_kpis() -> KPIReport:
    """
    Query the database and compute all KPIs.
    Returns a KPIReport dataclass.
    """
    today_str = datetime.date.today().isoformat()

    with get_db() as db:
        activities = db.query(ScheduleActivity).all()
        db.expunge_all()

    if not activities:
        return KPIReport(
            overall_progress=0.0,
            total_activities=0,
            completed_activities=0,
            on_track_count=0,
            at_risk_count=0,
            behind_count=0,
            auto_applied_count=0,
            pending_review_count=0,
            spi=1.0,
        )

    total = len(activities)
    progresses = [a.progress_pct or 0.0 for a in activities]
    overall_progress = sum(progresses) / total if total > 0 else 0.0
    completed = sum(1 for p in progresses if p >= 100.0)

    on_track, at_risk, behind = 0, 0, 0
    for a in activities:
        pct = a.progress_pct or 0.0
        if pct >= 100:
            on_track += 1
        elif a.planned_end and a.planned_end < today_str:
            # Overdue — check severity
            if pct >= 80:
                at_risk += 1
            else:
                behind += 1
        elif a.planned_end and a.planned_end > today_str:
            on_track += 1
        else:
            at_risk += 1

    # SPI: earned value / planned value (simplified)
    planned_progress = 0.0
    earned = 0.0
    for a in activities:
        if a.planned_start and a.planned_end:
            try:
                ps = datetime.date.fromisoformat(a.planned_start)
                pe = datetime.date.fromisoformat(a.planned_end)
                today = datetime.date.today()
                total_days = max((pe - ps).days, 1)
                elapsed = max(min((today - ps).days, total_days), 0)
                planned_pct = (elapsed / total_days) * 100.0
                planned_progress += planned_pct
                earned += a.progress_pct or 0.0
            except Exception:
                pass
    spi = (earned / planned_progress) if planned_progress > 0 else 1.0
    spi = round(min(spi, 2.0), 3)  # cap at 2.0

    # Discipline breakdown
    disc_map: dict[str, list[ScheduleActivity]] = {}
    for a in activities:
        disc_map.setdefault(a.discipline, []).append(a)

    discipline_kpis = []
    for disc, acts in disc_map.items():
        d_progresses = [a.progress_pct or 0.0 for a in acts]
        d_on_track, d_at_risk, d_behind = 0, 0, 0
        for a in acts:
            pct = a.progress_pct or 0.0
            if pct >= 100:
                d_on_track += 1
            elif a.planned_end and a.planned_end < today_str:
                if pct >= 80:
                    d_at_risk += 1
                else:
                    d_behind += 1
            else:
                d_on_track += 1
        discipline_kpis.append(DisciplineKPI(
            discipline=disc,
            total_activities=len(acts),
            avg_progress=sum(d_progresses) / len(d_progresses),
            on_track=d_on_track,
            at_risk=d_at_risk,
            behind=d_behind,
            completed=sum(1 for p in d_progresses if p >= 100),
        ))

    # Get event counts from DB
    from sitesync.db.models import EventLog, ReviewQueueItem
    with get_db() as db:
        auto_applied = db.query(EventLog).filter(EventLog.auto_applied == True).count()
        pending_review = db.query(ReviewQueueItem).filter(ReviewQueueItem.status == "PENDING").count()

    return KPIReport(
        overall_progress=round(overall_progress, 1),
        total_activities=total,
        completed_activities=completed,
        on_track_count=on_track,
        at_risk_count=at_risk,
        behind_count=behind,
        auto_applied_count=auto_applied,
        pending_review_count=pending_review,
        spi=spi,
        disciplines=sorted(discipline_kpis, key=lambda d: d.discipline),
    )
'''

files["sitesync/analytics/gantt_builder.py"] = '''"""
SiteSync AI — Gantt Chart Builder

Builds a professional Plotly Gantt chart with:
- Planned bars (transparent)
- Actual progress overlay
- Today's date line
- Status color coding (On Track / At Risk / Behind)
- Discipline grouping
"""
from __future__ import annotations

import datetime
from typing import Optional

import pandas as pd
import plotly.graph_objects as go

from sitesync.db.models import ScheduleActivity
from sitesync.db.session import get_db

def _get_status(activity: ScheduleActivity, today_str: str) -> str:
    pct = activity.progress_pct or 0.0
    if pct >= 100:
        return "Completed"
    if activity.planned_end and activity.planned_end < today_str:
        return "Behind" if pct < 80 else "At Risk"
    if activity.planned_end and activity.planned_end <= (datetime.date.today() + datetime.timedelta(days=7)).isoformat():
        if pct < 50:
            return "At Risk"
    return "On Track"

def build_gantt(
    discipline_filter: Optional[str] = None,
    max_activities: int = 40,
) -> go.Figure:
    """
    Build and return a Plotly Gantt figure.
    
    Args:
        discipline_filter: Optional discipline to filter by.
        max_activities: Max number of activities to display.
    
    Returns:
        Plotly Figure object.
    """
    today = datetime.date.today()
    today_str = today.isoformat()

    with get_db() as db:
        query = db.query(ScheduleActivity)
        if discipline_filter:
            query = query.filter(ScheduleActivity.discipline == discipline_filter)
        activities = query.limit(max_activities).all()
        db.expunge_all()

    if not activities:
        fig = go.Figure()
        fig.add_annotation(
            text="No schedule activities found. Please seed the database first.",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(size=16, color="#8B949E")
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0D1117",
            plot_bgcolor="#0D1117",
            height=400,
        )
        return fig

    status_colors = {
        "On Track": "#2EA043",
        "At Risk": "#D29922",
        "Behind": "#DA3633",
        "Completed": "#388BFD",
    }

    # Build planned bars
    planned_bars = []
    actual_bars = []

    for a in activities:
        if not a.planned_start or not a.planned_end:
            continue

        try:
            ps = datetime.date.fromisoformat(a.planned_start)
            pe = datetime.date.fromisoformat(a.planned_end)
        except ValueError:
            continue

        status = _get_status(a, today_str)
        color = status_colors.get(status, "#58A6FF")
        label = f"{a.activity_id}: {a.description[:35]}..."
        pct = a.progress_pct or 0.0

        # Planned bar (semi-transparent)
        planned_bars.append(dict(
            task=label,
            start=str(ps),
            finish=str(pe),
            status=status,
            discipline=a.discipline,
            progress=pct,
            activity_id=a.activity_id,
            color=color,
        ))

        # Actual progress bar
        total_days = max((pe - ps).days, 1)
        actual_days = int(total_days * pct / 100)
        actual_end = ps + datetime.timedelta(days=actual_days)
        actual_bars.append(dict(
            task=label,
            start=str(ps),
            finish=str(min(actual_end, pe)),
            progress=pct,
            color=color,
        ))

    if not planned_bars:
        fig = go.Figure()
        fig.add_annotation(text="No activities with planned dates found.", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
        return fig

    df_planned = pd.DataFrame(planned_bars)
    df_actual = pd.DataFrame(actual_bars)

    tasks = df_planned["task"].tolist()

    fig = go.Figure()

    # Add planned bars (light/transparent)
    for _, row in df_planned.iterrows():
        fig.add_trace(go.Bar(
            name=row["status"],
            x=[(pd.to_datetime(row["finish"]) - pd.to_datetime(row["start"])).days],
            y=[row["task"]],
            orientation="h",
            base=[pd.to_datetime(row["start"]).timestamp() * 1000],
            marker=dict(
                color=row["color"],
                opacity=0.25,
                line=dict(color=row["color"], width=1),
            ),
            hovertemplate=(
                f"<b>{row['activity_id']}</b><br>"
                f"Planned: {row['start']} → {row['finish']}<br>"
                f"Progress: {row['progress']:.0f}%<br>"
                f"Status: {row['status']}<extra></extra>"
            ),
            showlegend=False,
        ))

    # Add actual bars (solid)
    for _, row in df_actual.iterrows():
        dur = (pd.to_datetime(row["finish"]) - pd.to_datetime(row["start"])).days
        if dur <= 0:
            continue
        fig.add_trace(go.Bar(
            name="Actual",
            x=[dur],
            y=[row["task"]],
            orientation="h",
            base=[pd.to_datetime(row["start"]).timestamp() * 1000],
            marker=dict(
                color=row["color"],
                opacity=0.85,
            ),
            hovertemplate=f"Actual progress: {row['progress']:.0f}%<extra></extra>",
            showlegend=False,
        ))

    # Today's line
    today_ms = pd.to_datetime(today_str).timestamp() * 1000
    fig.add_shape(
        type="line",
        x0=today_ms, x1=today_ms,
        y0=-0.5, y1=len(tasks) - 0.5,
        line=dict(color="#F0A500", width=2, dash="dash"),
    )
    fig.add_annotation(
        x=today_ms, y=len(tasks) - 0.5,
        text="Today",
        showarrow=False,
        font=dict(color="#F0A500", size=11),
        yshift=10,
    )

    # Layout
    fig.update_layout(
        title=dict(
            text="📅 Project Schedule — Planned vs Actual",
            font=dict(size=16, color="#E6EDF3"),
        ),
        barmode="overlay",
        template="plotly_dark",
        paper_bgcolor="#0D1117",
        plot_bgcolor="#161B22",
        height=max(400, len(tasks) * 28 + 100),
        xaxis=dict(
            type="date",
            tickformat="%b %Y",
            gridcolor="#21262D",
            showgrid=True,
            title="",
            rangeslider=dict(visible=True, thickness=0.05),
        ),
        yaxis=dict(
            autorange="reversed",
            tickfont=dict(size=10),
            gridcolor="#21262D",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        margin=dict(l=20, r=20, t=60, b=40),
        hoverlabel=dict(
            bgcolor="#1C2128",
            bordercolor="#30363D",
            font=dict(color="#E6EDF3"),
        ),
    )

    return fig
'''

files["sitesync/analytics/forecaster.py"] = '''"""
SiteSync AI — Schedule Forecaster

Provides earned-value-based forecasting:
- Estimate completion date based on current SPI
- Identify critical activities that are behind
- Generate delay pattern insights
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Optional

from sitesync.db.models import ScheduleActivity
from sitesync.db.session import get_db

@dataclass
class ActivityForecast:
    activity_id: str
    description: str
    discipline: str
    planned_end: Optional[str]
    current_progress: float
    estimated_completion: Optional[str]
    delay_days: int
    is_critical: bool

@dataclass
class ProjectForecast:
    estimated_completion_date: Optional[str]
    baseline_completion_date: Optional[str]
    delay_days: int
    spi: float
    critical_activities: list[ActivityForecast]
    at_risk_activities: list[ActivityForecast]
    generated_at: str = ""

    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.datetime.now().isoformat()

def compute_forecast() -> ProjectForecast:
    """Compute project-level schedule forecast."""
    today = datetime.date.today()
    today_str = today.isoformat()

    with get_db() as db:
        activities = db.query(ScheduleActivity).all()
        db.expunge_all()

    if not activities:
        return ProjectForecast(
            estimated_completion_date=None,
            baseline_completion_date=None,
            delay_days=0,
            spi=1.0,
            critical_activities=[],
            at_risk_activities=[],
        )

    # Find project baseline end
    planned_ends = [a.planned_end for a in activities if a.planned_end]
    baseline_end = max(planned_ends) if planned_ends else None

    critical = []
    at_risk = []

    for a in activities:
        pct = a.progress_pct or 0.0
        if pct >= 100 or not a.planned_start or not a.planned_end:
            continue

        try:
            ps = datetime.date.fromisoformat(a.planned_start)
            pe = datetime.date.fromisoformat(a.planned_end)
        except ValueError:
            continue

        total_days = max((pe - ps).days, 1)
        elapsed = max((today - ps).days, 0)

        # Expected progress by today
        expected_pct = min((elapsed / total_days) * 100, 100)

        # Estimate completion based on current velocity
        remaining_pct = 100 - pct
        if pct > 0 and elapsed > 0:
            daily_rate = pct / elapsed
            days_to_complete = remaining_pct / daily_rate if daily_rate > 0 else total_days * 2
        else:
            days_to_complete = total_days * 2

        est_completion = today + datetime.timedelta(days=int(days_to_complete))
        delay_days = max((est_completion - pe).days, 0)

        forecast = ActivityForecast(
            activity_id=a.activity_id,
            description=a.description[:60],
            discipline=a.discipline,
            planned_end=a.planned_end,
            current_progress=pct,
            estimated_completion=est_completion.isoformat(),
            delay_days=delay_days,
            is_critical=(a.planned_end and a.planned_end < today_str and pct < 100),
        )

        variance = pct - expected_pct
        if variance < -20 or (a.planned_end and a.planned_end < today_str):
            critical.append(forecast)
        elif variance < -10:
            at_risk.append(forecast)

    # Project SPI
    planned_sum, earned_sum = 0.0, 0.0
    for a in activities:
        if a.planned_start and a.planned_end:
            try:
                ps = datetime.date.fromisoformat(a.planned_start)
                pe = datetime.date.fromisoformat(a.planned_end)
                total_days = max((pe - ps).days, 1)
                elapsed = max(min((today - ps).days, total_days), 0)
                planned_sum += (elapsed / total_days) * 100
                earned_sum += a.progress_pct or 0.0
            except Exception:
                pass
    spi = round(earned_sum / planned_sum, 3) if planned_sum > 0 else 1.0

    # Estimate project completion
    if baseline_end and spi > 0:
        try:
            be = datetime.date.fromisoformat(baseline_end)
            total_project_days = max((be - datetime.date(2025, 1, 1)).days, 1)
            projected_days = int(total_project_days / spi)
            est_project_completion = (datetime.date(2025, 1, 1) + datetime.timedelta(days=projected_days)).isoformat()
        except Exception:
            est_project_completion = None
    else:
        est_project_completion = None

    try:
        delay_days = max((datetime.date.fromisoformat(est_project_completion) - datetime.date.fromisoformat(baseline_end)).days, 0) if est_project_completion and baseline_end else 0
    except Exception:
        delay_days = 0

    return ProjectForecast(
        estimated_completion_date=est_project_completion,
        baseline_completion_date=baseline_end,
        delay_days=delay_days,
        spi=spi,
        critical_activities=sorted(critical, key=lambda x: x.delay_days, reverse=True)[:10],
        at_risk_activities=sorted(at_risk, key=lambda x: x.delay_days, reverse=True)[:10],
    )
'''

files["sitesync/linking/raptor_match.py"] = '''"""
SiteSync AI — Hybrid Activity Matcher (Semantic + RapidFuzz)

Extends the base semantic matcher with RapidFuzz token_sort_ratio
for construction-domain fuzzy string matching.

Hybrid score = 0.65 * semantic_cosine + 0.35 * fuzzy_ratio

Also includes a construction abbreviation expander to normalize
field jargon before matching.
"""
from __future__ import annotations

from typing import Optional

from sitesync.extraction.schemas import ActivityUpdate
from sitesync.linking.matcher import LinkingResult, MatchResult, get_matcher

# Construction domain abbreviation dictionary
ABBREV_MAP = {
    "rcc": "reinforced cement concrete",
    "pcc": "plain cement concrete",
    "wbs": "work breakdown structure",
    "mep": "mechanical electrical plumbing",
    "jcb": "excavator backhoe",
    "hse": "health safety environment",
    "cpm": "critical path method",
    "di": "ductile iron",
    "gi": "galvanized iron",
    "ms": "mild steel",
    "cs": "carbon steel",
    "ss": "stainless steel",
    "f/w": "formwork",
    "r/f": "reinforcement",
    "exc": "excavation",
    "backfill": "backfilling",
    "inst": "instrumentation",
    "elec": "electrical",
    "hvac": "heating ventilation air conditioning",
    "epc": "engineering procurement construction",
    "piping": "pipe pipeline piping",
    "spool": "prefabricated pipe spool",
}

def _expand_abbreviations(text: str) -> str:
    """Expand construction abbreviations in text."""
    words = text.lower().split()
    expanded = [ABBREV_MAP.get(w, w) for w in words]
    return " ".join(expanded)

def hybrid_match(
    update: ActivityUpdate,
    top_k: int = 3,
    min_semantic_score: float = 0.25,
) -> LinkingResult:
    """
    Hybrid activity matching: semantic similarity + RapidFuzz fuzzy matching.
    Falls back gracefully if rapidfuzz is not installed.
    """
    matcher = get_matcher()
    result = matcher.match(update, top_k=top_k * 2, min_semantic_score=min_semantic_score)

    if result.is_unmatched or not result.top_matches:
        return result

    try:
        from rapidfuzz import fuzz
        expanded_query = _expand_abbreviations(update.activity_description)

        enhanced_matches = []
        for match in result.top_matches:
            expanded_desc = _expand_abbreviations(match.description)
            fuzzy_score = fuzz.token_sort_ratio(expanded_query, expanded_desc) / 100.0

            # Hybrid score: 65% semantic + 35% fuzzy
            hybrid_score = 0.65 * match.semantic_score + 0.35 * fuzzy_score

            from sitesync.linking.confidence import compute_confidence
            conf, s, e, t = compute_confidence(
                semantic_score=hybrid_score,
                evidence_type=update.evidence_type,
                report_date=update.date,
                planned_start=match.planned_start,
                planned_end=match.planned_end,
            )

            enhanced_matches.append(MatchResult(
                activity_id=match.activity_id,
                description=match.description,
                discipline=match.discipline,
                location=match.location,
                planned_start=match.planned_start,
                planned_end=match.planned_end,
                wbs_code=match.wbs_code,
                semantic_score=hybrid_score,
                evidence_weight=e,
                temporal_score=t,
                confidence=conf,
                rank=0,
            ))

        enhanced_matches.sort(key=lambda m: m.confidence, reverse=True)
        for i, m in enumerate(enhanced_matches[:top_k], start=1):
            m.rank = i

        top_k_matches = enhanced_matches[:top_k]
        best = top_k_matches[0] if top_k_matches else None
        is_unmatched = best is None or best.confidence < 0.30

        return LinkingResult(
            update=update,
            top_matches=top_k_matches,
            best_match=best,
            is_unmatched=is_unmatched,
        )

    except ImportError:
        return result
'''

files["sitesync/ingestion/voice_agent.py"] = '''"""
SiteSync AI — Voice Input Agent

Provides speech-to-text transcription for field supervisor voice input.
Priority:
  1. faster-whisper (offline, local)
  2. SpeechRecognition + Google STT (requires internet)
  3. Text-only fallback
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from rich.console import Console

console = Console()

def transcribe_audio(audio_path: str | Path) -> Optional[str]:
    """Transcribe an audio file to text."""
    audio_path = Path(audio_path)
    if not audio_path.exists():
        console.print(f"[red]Audio file not found: {audio_path}[/red]")
        return None

    result = _transcribe_whisper(audio_path)
    if result is not None:
        return result

    result = _transcribe_speech_recognition(audio_path)
    if result is not None:
        return result

    console.print("[yellow]⚠ Voice transcription not available. Please type your update.[/yellow]")
    return None

def _transcribe_whisper(audio_path: Path) -> Optional[str]:
    try:
        from faster_whisper import WhisperModel

        console.print("[dim]🎤 Transcribing with Whisper (offline)...[/dim]")
        model = WhisperModel("base", device="cpu", compute_type="int8")

        segments, info = model.transcribe(
            str(audio_path),
            language="en",
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
            initial_prompt=(
                "Construction progress report. WBS, formwork, reinforcement, concreting, "
                "earthworks, piping, spool, CPM schedule, discipline, zone, percent complete."
            ),
        )

        text = " ".join(seg.text.strip() for seg in segments)
        console.print(f"[green]✅ Whisper transcription: {text[:80]}...[/green]")
        return text.strip() if text.strip() else None

    except ImportError:
        console.print("[dim]faster-whisper not installed, trying fallback...[/dim]")
        return None
    except Exception as e:
        console.print(f"[yellow]Whisper error: {e}[/yellow]")
        return None

def _transcribe_speech_recognition(audio_path: Path) -> Optional[str]:
    try:
        import speech_recognition as sr

        console.print("[dim]🎤 Transcribing with Google STT...[/dim]")
        recognizer = sr.Recognizer()

        wav_path = audio_path
        if audio_path.suffix.lower() not in ('.wav',):
            try:
                import subprocess
                wav_path = audio_path.with_suffix('.wav')
                subprocess.run(['ffmpeg', '-i', str(audio_path), str(wav_path), '-y'], capture_output=True, timeout=30)
            except Exception:
                pass

        with sr.AudioFile(str(wav_path)) as source:
            audio = recognizer.record(source)

        text = recognizer.recognize_google(audio)
        console.print(f"[green]✅ Google STT: {text[:80]}[/green]")
        return text

    except ImportError:
        console.print("[dim]SpeechRecognition not installed.[/dim]")
        return None
    except Exception as e:
        console.print(f"[yellow]Google STT error: {e}[/yellow]")
        return None

def is_voice_available() -> bool:
    try:
        import faster_whisper
        return True
    except ImportError:
        pass
    try:
        import speech_recognition
        return True
    except ImportError:
        pass
    return False
'''

# Now write them
base_dir = Path(r"C:\Users\prish\.gemini\antigravity\scratch\SiteSyncAI")
for filepath, content in files.items():
    p = base_dir / filepath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    print(f"Created/Modified: {p}")
