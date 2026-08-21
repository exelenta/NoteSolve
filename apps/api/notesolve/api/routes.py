from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from notesolve.api.schemas import CreateDocumentResponse, HealthResponse, JobStatusResponse
from notesolve.config import Settings, get_settings
from notesolve.domain.models import LOCAL_WORKSPACE_ID, DocumentStatus, PipelineStage
from notesolve.infrastructure.db import get_session
from notesolve.infrastructure.local_storage import LocalStorageProvider
from notesolve.infrastructure.tables import DocumentRow, PipelineJobRow

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
