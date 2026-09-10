"""
Tests for the ChromaDB institutional memory store.
Uses a temporary ChromaDB directory for complete isolation.
"""
import pytest
import json


@pytest.fixture
def tmp_chroma(tmp_path, monkeypatch):
    """Override chroma persist dir to a unique tmp directory."""
    chroma_dir = str(tmp_path / "test_chroma_mem")
    monkeypatch.setattr("sitesync.config.settings.chroma_persist_dir", chroma_dir)
    return chroma_dir


class TestMemoryStore:
    """Tests for upsert_event() and query_memory()."""

    def test_upsert_event_does_not_crash(self, tmp_chroma):
        """upsert_event should persist without error."""
        from sitesync.memory.chroma_store import upsert_event
        upsert_event(
            event_id=1,
            activity_id="PIPING-001",
            discipline="Piping",
            activity_description="Welding spools on hot oil line",
            actual_progress_pct=35.0,
            report_date="2026-09-10",
            evidence_type="text",
            planned_start="2026-01-15",
            planned_end="2026-04-15",
            confidence_score=0.91,
        )

    def test_upsert_then_query_returns_result(self, tmp_chroma):
        """After upserting an event, querying for it should return results."""
        from sitesync.memory.chroma_store import upsert_event, query_memory

        upsert_event(
            event_id=10,
            activity_id="CIVIL-001",
            discipline="Civil",
            activity_description="Excavation for column footing Zone A",
            actual_progress_pct=60.0,
            report_date="2026-09-10",
            evidence_type="spreadsheet",
            confidence_score=0.88,
        )

        results = query_memory("excavation footing", n_results=5)
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_query_result_has_expected_keys(self, tmp_chroma):
        """Each result should have 'document', 'metadata', 'similarity'."""
        from sitesync.memory.chroma_store import upsert_event, query_memory

        upsert_event(
            event_id=20,
            activity_id="ELEC-001",
            discipline="Electrical",
            activity_description="Cable tray installation unit 1",
            actual_progress_pct=90.0,
            report_date="2026-09-10",
            evidence_type="text",
            confidence_score=0.72,
        )

        results = query_memory("cable tray", n_results=3)
        for r in results:
            assert "document" in r
            assert "metadata" in r
            assert "similarity" in r

    def test_query_similarity_in_range(self, tmp_chroma):
        """Similarity scores should be in [0, 1]."""
        from sitesync.memory.chroma_store import upsert_event, query_memory

        upsert_event(
            event_id=30,
            activity_id="HSE-001",
            discipline="HSE",
            activity_description="Safety induction and toolbox talk",
            actual_progress_pct=100.0,
            report_date="2026-09-10",
            evidence_type="text",
            confidence_score=0.95,
        )

        results = query_memory("safety toolbox talk HSE", n_results=3)
        for r in results:
            assert 0.0 <= r["similarity"] <= 1.0

    def test_upsert_idempotent(self, tmp_chroma):
        """Upserting the same event_id twice should not create duplicates."""
        from sitesync.memory.chroma_store import upsert_event, memory_stats

        for _ in range(2):
            upsert_event(
                event_id=99,
                activity_id="INST-001",
                discipline="Instrumentation",
                activity_description="Install transmitters on Tank T-01",
                actual_progress_pct=50.0,
                report_date="2026-09-10",
                evidence_type="text",
                confidence_score=0.80,
            )

        stats = memory_stats()
        # Only 1 record should exist for event_id=99
        assert stats["total_events"] == 1

    def test_memory_stats_returns_dict(self, tmp_chroma):
        """memory_stats() should always return a dict."""
        from sitesync.memory.chroma_store import memory_stats
        stats = memory_stats()
        assert isinstance(stats, dict)
        assert "total_events" in stats

    def test_query_with_discipline_filter(self, tmp_chroma):
        """Discipline filter should restrict results."""
        from sitesync.memory.chroma_store import upsert_event, query_memory

        upsert_event(
            event_id=40,
            activity_id="PIPING-002",
            discipline="Piping",
            activity_description="Pressure test on hot oil line",
            actual_progress_pct=0.0,
            report_date="2026-09-10",
            evidence_type="text",
            confidence_score=0.65,
        )
        upsert_event(
            event_id=41,
            activity_id="CIVIL-002",
            discipline="Civil",
            activity_description="Concrete pour at foundation grid B3",
            actual_progress_pct=85.0,
            report_date="2026-09-10",
            evidence_type="text",
            confidence_score=0.88,
        )

        results = query_memory("pipeline pressure test", discipline_filter="Piping", n_results=5)
        for r in results:
            assert r["metadata"]["discipline"] == "Piping"

    def test_query_constraints_stored_as_json(self, tmp_chroma):
        """Constraints list should be stored as JSON-serializable string."""
        from sitesync.memory.chroma_store import upsert_event, query_memory

        constraints = ["Material shortage — SS consumables", "Scaffold inspection pending"]
        upsert_event(
            event_id=50,
            activity_id="PIPING-003",
            discipline="Piping",
            activity_description="3-inch SS line spool erection utility area",
            actual_progress_pct=40.0,
            report_date="2026-09-10",
            evidence_type="text",
            confidence_score=0.70,
            constraints=constraints,
        )

        results = query_memory("SS line spool utility", n_results=5)
        assert len(results) >= 1
        stored_constraints = results[0]["metadata"].get("constraints", "[]")
        parsed = json.loads(stored_constraints)
        assert isinstance(parsed, list)
