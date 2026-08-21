from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from notesolve.application.analysis import AnalysisService
from notesolve.config import Settings, get_settings
from notesolve.infrastructure.db import SessionLocal
from notesolve.infrastructure.local_storage import LocalStorageProvider
from notesolve.providers.factory import create_worksheet_analyzer, create_worksheet_verifier

AnalysisTask = Callable[[UUID], Awaitable[None]]


def get_analysis_task(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnalysisTask:
    analyzer = create_worksheet_analyzer(settings)
    verifier = create_worksheet_verifier(settings)

    async def run_analysis_job(job_id: UUID) -> None:
        with SessionLocal() as session:
            service = AnalysisService(
                session=session,
                storage=LocalStorageProvider(settings.data_dir / "objects"),
                analyzer=analyzer,
                verifier=verifier,
                verification_threshold=settings.verification_threshold,
            )
            await service.run(job_id)

    return run_analysis_job
