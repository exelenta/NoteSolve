from collections.abc import Awaitable, Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends

from notesolve.application.agent_edit import AgentEditService
from notesolve.application.analysis import AnalysisService
from notesolve.config import Settings, get_settings
from notesolve.infrastructure.db import SessionLocal
from notesolve.infrastructure.local_storage import LocalStorageProvider
from notesolve.infrastructure.local_vault import LocalVaultRepository
from notesolve.providers.factory import (
    create_vault_note_editor,
    create_worksheet_analyzer,
    create_worksheet_verifier,
)

AnalysisTask = Callable[[UUID], Awaitable[None]]
AgentEditTask = Callable[[UUID], Awaitable[None]]


def get_analysis_task(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AnalysisTask:
    async def run_analysis_job(job_id: UUID) -> None:
        with SessionLocal() as session:
            service = AnalysisService(
                session=session,
                storage=LocalStorageProvider(settings.data_dir / "objects"),
                analyzer=create_worksheet_analyzer(settings),
                verifier=create_worksheet_verifier(settings),
                verification_threshold=settings.verification_threshold,
            )
            await service.run(job_id)

    return run_analysis_job


def get_agent_edit_task(
    settings: Annotated[Settings, Depends(get_settings)],
) -> AgentEditTask:
    async def run_agent_edit_job(job_id: UUID) -> None:
        with SessionLocal() as session:
            service = AgentEditService(
                session=session,
                vault=LocalVaultRepository(settings.resolved_vault_dir),
                editor=create_vault_note_editor(settings),
            )
            await service.run(job_id)

    return run_agent_edit_job
