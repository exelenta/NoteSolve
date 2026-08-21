from datetime import datetime
from uuid import UUID

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from notesolve.domain.models import DocumentStatus, PipelineStage, utcnow
from notesolve.infrastructure.db import Base


class DocumentRow(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("workspace_id", "content_hash"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    size_bytes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default=DocumentStatus.INGESTED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PipelineJobRow(Base):
    __tablename__ = "pipeline_jobs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(index=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    stage: Mapped[str] = mapped_column(String(50), default=PipelineStage.INGESTED)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class WorksheetResultRow(Base):
    __tablename__ = "worksheet_results"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(index=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), unique=True, index=True)
    job_id: Mapped[UUID] = mapped_column(ForeignKey("pipeline_jobs.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(100))
    prompt_version: Mapped[str] = mapped_column(String(100))
    result_json: Mapped[dict[str, object]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class VaultChangeSetRow(Base):
    __tablename__ = "vault_change_sets"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    workspace_id: Mapped[UUID] = mapped_column(index=True)
    document_id: Mapped[UUID] = mapped_column(ForeignKey("documents.id"), index=True)
    status: Mapped[str] = mapped_column(String(50))
    base_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    operations_json: Mapped[list[dict[str, object]]] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(String(500))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VaultRevisionRow(Base):
    __tablename__ = "vault_revisions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    change_set_id: Mapped[UUID] = mapped_column(
        ForeignKey("vault_change_sets.id"), unique=True, index=True
    )
    path: Mapped[str] = mapped_column(String(500))
    previous_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
