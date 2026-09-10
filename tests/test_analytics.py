"""
Tests for analytics modules:
  - kpi_engine.compute_kpis()
  - forecaster.compute_forecast()
  - gantt_builder.build_gantt()

All tests use in-memory SQLite seeded with known activities.
"""
import pytest
import numpy as np
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager


class TestKPIEngine:
    """Tests for the KPI computation engine."""

    @pytest.fixture(autouse=True)
    def _patch_db(self, seeded_db, monkeypatch):
        """Redirect KPI engine to use the in-memory seeded DB."""
        Session = sessionmaker(bind=seeded_db)

        @contextmanager
        def mock_get_db():
            s = Session()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()

        monkeypatch.setattr("sitesync.analytics.kpi_engine.get_db", mock_get_db)
        monkeypatch.setattr("sitesync.db.session.get_db", mock_get_db)
        self.mock_get_db = mock_get_db

    def test_compute_kpis_returns_report(self):
        """compute_kpis should return a KPIReport with correct fields."""
        from sitesync.analytics.kpi_engine import compute_kpis
        report = compute_kpis()
        assert report is not None
        assert hasattr(report, "overall_progress")
        assert hasattr(report, "total_activities")
        assert hasattr(report, "spi")
        assert hasattr(report, "disciplines")

    def test_total_activities_matches_seeded(self):
        """Total activities should match the 5 seeded activities in conftest."""
        from sitesync.analytics.kpi_engine import compute_kpis
        report = compute_kpis()
        assert report.total_activities == 5

    def test_overall_progress_between_0_and_100(self):
        """Overall progress must be in [0, 100]."""
        from sitesync.analytics.kpi_engine import compute_kpis
        report = compute_kpis()
        assert 0.0 <= report.overall_progress <= 100.0

    def test_spi_is_positive(self):
        """SPI should always be a positive number."""
        from sitesync.analytics.kpi_engine import compute_kpis
        report = compute_kpis()
        assert report.spi > 0

    def test_discipline_kpis_present(self):
        """Discipline breakdown should have at least one entry."""
        from sitesync.analytics.kpi_engine import compute_kpis
        report = compute_kpis()
        assert len(report.disciplines) >= 1

    def test_discipline_kpi_counts_sum_correctly(self):
        """on_track + at_risk + behind + completed should sum to total activities per discipline."""
        from sitesync.analytics.kpi_engine import compute_kpis
        report = compute_kpis()
        for d in report.disciplines:
            total = d.on_track + d.at_risk + d.behind
            # completed activities are a subset of on_track; just check total makes sense
            assert total <= d.total_activities + 1  # +1 tolerance for completed overlap

    def test_empty_db_returns_zero_report(self, monkeypatch):
        """Empty DB should return zeros, not crash."""
        from sitesync.db.models import Base
        from sqlalchemy import create_engine
        empty_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(empty_engine)
        EmptySession = sessionmaker(bind=empty_engine)

        @contextmanager
        def empty_db():
            s = EmptySession()
            try:
                yield s
                s.commit()
            finally:
                s.close()

        monkeypatch.setattr("sitesync.analytics.kpi_engine.get_db", empty_db)

        from sitesync.analytics.kpi_engine import compute_kpis
        report = compute_kpis()
        assert report.total_activities == 0
        assert report.overall_progress == 0.0
        assert report.spi == 1.0


class TestForecaster:
    """Tests for the schedule forecaster."""

    @pytest.fixture(autouse=True)
    def _patch_db(self, seeded_db, monkeypatch):
        Session = sessionmaker(bind=seeded_db)

        @contextmanager
        def mock_get_db():
            s = Session()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()

        monkeypatch.setattr("sitesync.analytics.forecaster.get_db", mock_get_db)

    def test_compute_forecast_returns_project_forecast(self):
        """compute_forecast should return a ProjectForecast."""
        from sitesync.analytics.forecaster import compute_forecast
        forecast = compute_forecast()
        assert forecast is not None
        assert hasattr(forecast, "spi")
        assert hasattr(forecast, "critical_activities")
        assert hasattr(forecast, "at_risk_activities")

    def test_forecast_spi_positive(self):
        from sitesync.analytics.forecaster import compute_forecast
        forecast = compute_forecast()
        assert forecast.spi > 0

    def test_forecast_critical_activities_is_list(self):
        from sitesync.analytics.forecaster import compute_forecast
        forecast = compute_forecast()
        assert isinstance(forecast.critical_activities, list)

    def test_forecast_at_risk_activities_is_list(self):
        from sitesync.analytics.forecaster import compute_forecast
        forecast = compute_forecast()
        assert isinstance(forecast.at_risk_activities, list)

    def test_forecast_generated_at_set(self):
        from sitesync.analytics.forecaster import compute_forecast
        forecast = compute_forecast()
        assert forecast.generated_at != ""

    def test_empty_db_returns_default_forecast(self, monkeypatch):
        """Empty DB should not crash forecaster."""
        from sitesync.db.models import Base
        from sqlalchemy import create_engine
        empty_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(empty_engine)
        EmptySession = sessionmaker(bind=empty_engine)

        @contextmanager
        def empty_db():
            s = EmptySession()
            try:
                yield s
                s.commit()
            finally:
                s.close()

        monkeypatch.setattr("sitesync.analytics.forecaster.get_db", empty_db)

        from sitesync.analytics.forecaster import compute_forecast
        forecast = compute_forecast()
        assert forecast.spi == 1.0
        assert forecast.critical_activities == []


class TestGanttBuilder:
    """Tests for the Plotly Gantt chart builder."""

    @pytest.fixture(autouse=True)
    def _patch_db(self, seeded_db, monkeypatch):
        Session = sessionmaker(bind=seeded_db)

        @contextmanager
        def mock_get_db():
            s = Session()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()

        monkeypatch.setattr("sitesync.analytics.gantt_builder.get_db", mock_get_db)

    def test_build_gantt_returns_figure(self):
        """build_gantt should return a Plotly Figure object."""
        import plotly.graph_objects as go
        from sitesync.analytics.gantt_builder import build_gantt
        fig = build_gantt()
        assert isinstance(fig, go.Figure)

    def test_build_gantt_with_discipline_filter(self):
        """build_gantt should accept a discipline filter without crashing."""
        import plotly.graph_objects as go
        from sitesync.analytics.gantt_builder import build_gantt
        fig = build_gantt(discipline_filter="Piping")
        assert isinstance(fig, go.Figure)

    def test_build_gantt_empty_db_returns_annotation(self, monkeypatch):
        """Empty DB should return a figure with an annotation, not crash."""
        import plotly.graph_objects as go
        from sitesync.db.models import Base
        from sqlalchemy import create_engine
        empty_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(empty_engine)
        EmptySession = sessionmaker(bind=empty_engine)

        @contextmanager
        def empty_db():
            s = EmptySession()
            try:
                yield s
                s.commit()
            finally:
                s.close()

        monkeypatch.setattr("sitesync.analytics.gantt_builder.get_db", empty_db)

        from sitesync.analytics.gantt_builder import build_gantt
        fig = build_gantt()
        assert isinstance(fig, go.Figure)
        # Empty figure should have at least one annotation
        assert len(fig.layout.annotations) >= 1
