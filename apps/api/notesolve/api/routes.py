from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from notesolve.api.schemas import (
    AnalyzeJobResponse,
    CreateDocumentResponse,
    HealthResponse,
    JobStatusResponse,
    VaultChangeSetResponse,
    VaultPreviewResponse,
    WorksheetResultResponse,
)
from notesolve.application.markdown import build_vault_preview
from notesolve.application.tasks import AnalysisTask, get_analysis_task
from notesolve.application.vault import VaultChangeSetService
from notesolve.config import Settings, get_settings
from notesolve.domain.models import (
    LOCAL_WORKSPACE_ID,
    DocumentStatus,
    PipelineStage,
    VaultChangeSetStatus,
    WorksheetResult,
)
from notesolve.infrastructure.db import get_session
from notesolve.infrastructure.local_storage import LocalStorageProvider
from notesolve.infrastructure.local_vault import LocalVaultRepository, VaultConflictError
from notesolve.infrastructure.tables import (
    DocumentRow,
    PipelineJobRow,
    VaultChangeSetRow,
    WorksheetResultRow,
)

router = APIRouter()
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "application/pdf"}


async def limited_chunks(file: UploadFile, limit: int) -> AsyncIterator[bytes]:
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="File exceeds the configured upload limit",
            )
        yield chunk


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="notesolve-api", version="0.1.0")


@router.post(
    "/documents",
    response_model=CreateDocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    file: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CreateDocumentResponse:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=415, detail="Only JPG, PNG, and PDF files are supported")
    filename = file.filename or "upload.bin"
    document_id = uuid4()
    storage = LocalStorageProvider(settings.data_dir / "objects")
    storage_key, content_hash, size_bytes = await storage.save(
        workspace_id=LOCAL_WORKSPACE_ID,
        document_id=document_id,
        filename=filename,
        chunks=limited_chunks(file, settings.max_upload_bytes),
    )

    existing = session.scalar(
        select(DocumentRow).where(
            DocumentRow.workspace_id == LOCAL_WORKSPACE_ID,
            DocumentRow.content_hash == content_hash,
        )
    )
    if existing is not None:
        storage.delete(storage_key)
        existing_job = session.scalar(
            select(PipelineJobRow)
            .where(PipelineJobRow.document_id == existing.id)
            .order_by(PipelineJobRow.created_at.desc())
        )
        if existing_job is None:
            existing_job = PipelineJobRow(
                id=uuid4(),
                workspace_id=LOCAL_WORKSPACE_ID,
                document_id=existing.id,
                stage=PipelineStage.INGESTED,
                progress=0,
            )
            session.add(existing_job)
            session.commit()
        return CreateDocumentResponse(
            document_id=existing.id,
            job_id=existing_job.id,
            status=existing.status,
            duplicate=True,
        )

    document = DocumentRow(
        id=document_id,
        workspace_id=LOCAL_WORKSPACE_ID,
        original_filename=filename,
        content_type=file.content_type,
        storage_key=storage_key,
        content_hash=content_hash,
        size_bytes=size_bytes,
        status=DocumentStatus.INGESTED,
    )
    job = PipelineJobRow(
        id=uuid4(),
        workspace_id=LOCAL_WORKSPACE_ID,
        document_id=document_id,
        stage=PipelineStage.INGESTED,
        progress=0,
    )
    session.add_all([document, job])
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        storage.delete(storage_key)
        raise HTTPException(status_code=409, detail="Document already exists") from None
    return CreateDocumentResponse(
        document_id=document.id,
        job_id=job.id,
        status=document.status,
        duplicate=False,
    )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job(job_id: UUID, session: Annotated[Session, Depends(get_session)]) -> JobStatusResponse:
    job = session.get(PipelineJobRow, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobStatusResponse(
        job_id=job.id,
        document_id=job.document_id,
        stage=PipelineStage(job.stage),
        progress=job.progress,
        error_code=job.error_code,
        error_message=job.error_message,
    )


@router.post(
    "/jobs/{job_id}/analyze",
    response_model=AnalyzeJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def analyze_job(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    session: Annotated[Session, Depends(get_session)],
    analysis_task: Annotated[AnalysisTask, Depends(get_analysis_task)],
) -> AnalyzeJobResponse:
    job = session.get(PipelineJobRow, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.stage == PipelineStage.FAILED:
        job.error_code = None
        job.error_message = None
        job.stage = PipelineStage.INGESTED
        session.commit()
    background_tasks.add_task(analysis_task, job_id)
    return AnalyzeJobResponse(job_id=job_id, status="accepted")


@router.get(
    "/documents/{document_id}/result",
    response_model=WorksheetResultResponse,
)
def get_document_result(
    document_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> WorksheetResultResponse:
    row = session.scalar(
        select(WorksheetResultRow).where(WorksheetResultRow.document_id == document_id)
    )
    if row is None:
        document = session.get(DocumentRow, document_id)
        if document is None:
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=409, detail="Document analysis is not complete")
    return WorksheetResultResponse(
        document_id=row.document_id,
        job_id=row.job_id,
        provider=row.provider,
        model=row.model,
        prompt_version=row.prompt_version,
        result=WorksheetResult.model_validate(row.result_json),
    )


@router.get(
    "/documents/{document_id}/vault-preview",
    response_model=VaultPreviewResponse,
)
def get_vault_preview(
    document_id: UUID,
    session: Annotated[Session, Depends(get_session)],
) -> VaultPreviewResponse:
    document = session.get(DocumentRow, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    row = session.scalar(
        select(WorksheetResultRow).where(WorksheetResultRow.document_id == document_id)
    )
    if row is None:
        raise HTTPException(status_code=409, detail="Document analysis is not complete")
    result = WorksheetResult.model_validate(row.result_json)
    return VaultPreviewResponse(
        document_id=document_id,
        change_set=build_vault_preview(
            document_id=document_id,
            original_filename=document.original_filename,
            result=result,
        ),
    )


def _vault_response(
    row: VaultChangeSetRow,
    service: VaultChangeSetService,
) -> VaultChangeSetResponse:
    return VaultChangeSetResponse(
        document_id=row.document_id,
        status=VaultChangeSetStatus(row.status),
        error_message=row.error_message,
        change_set=service.to_domain(row),
    )


@router.post(
    "/documents/{document_id}/vault-change-sets",
    response_model=VaultChangeSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_vault_change_set(
    document_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VaultChangeSetResponse:
    service = VaultChangeSetService(
        session=session,
        vault=LocalVaultRepository(settings.resolved_vault_dir),
    )
    try:
        row = service.create(document_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _vault_response(row, service)


@router.get("/vault-change-sets/{change_set_id}", response_model=VaultChangeSetResponse)
def get_vault_change_set(
    change_set_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VaultChangeSetResponse:
    service = VaultChangeSetService(
        session=session,
        vault=LocalVaultRepository(settings.resolved_vault_dir),
    )
    try:
        row = service.get(change_set_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _vault_response(row, service)


@router.post("/vault-change-sets/{change_set_id}/apply", response_model=VaultChangeSetResponse)
def apply_vault_change_set(
    change_set_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VaultChangeSetResponse:
    service = VaultChangeSetService(
        session=session,
        vault=LocalVaultRepository(settings.resolved_vault_dir),
    )
    try:
        row = service.apply(change_set_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, VaultConflictError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _vault_response(row, service)


@router.post("/vault-change-sets/{change_set_id}/rollback", response_model=VaultChangeSetResponse)
def rollback_vault_change_set(
    change_set_id: UUID,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VaultChangeSetResponse:
    service = VaultChangeSetService(
        session=session,
        vault=LocalVaultRepository(settings.resolved_vault_dir),
    )
    try:
        row = service.rollback(change_set_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (RuntimeError, VaultConflictError) as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _vault_response(row, service)
