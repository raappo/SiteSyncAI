"""
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
