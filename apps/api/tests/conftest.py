from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from notesolve.application.analysis import AnalysisService
from notesolve.application.tasks import get_analysis_task
from notesolve.config import Settings, get_settings
from notesolve.infrastructure.db import Base, get_session
from notesolve.infrastructure.local_storage import LocalStorageProvider
from notesolve.main import app
from notesolve.providers.fake_analyzer import FakeWorksheetAnalyzer
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)
    settings = Settings(data_dir=tmp_path / "data", max_upload_mb=1)

    def session_override():
        with session_factory() as session:
            yield session

    async def analysis_task_override(job_id):
        with session_factory() as session:
            service = AnalysisService(
                session=session,
                storage=LocalStorageProvider(settings.data_dir / "objects"),
                analyzer=FakeWorksheetAnalyzer(),
            )
            await service.run(job_id)

    app.dependency_overrides[get_session] = session_override
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_analysis_task] = lambda: analysis_task_override
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
