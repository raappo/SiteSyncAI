"""
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
        data = '''```json
[{"discipline": "Civil", "location": "Zone A", "activity_description": "Excavation works", "actual_progress_pct": 50.0, "date": "2026-09-10", "evidence_type": "text"}]
```'''
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
