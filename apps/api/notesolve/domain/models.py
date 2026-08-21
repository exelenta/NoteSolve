from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

LOCAL_WORKSPACE_ID = UUID("00000000-0000-0000-0000-000000000001")


class DocumentStatus(StrEnum):
    INGESTED = "ingested"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStage(StrEnum):
    INGESTED = "ingested"
    ANALYZING = "analyzing"
    VALIDATING = "validating"
    VERIFYING = "verifying"
    FORMATTING = "formatting"
    VAULT_PREVIEW = "vault_preview"
    COMPLETED = "completed"
    FAILED = "failed"


class VerificationStatus(StrEnum):
    SELF_CHECKED = "self_checked"
    VERIFIED = "verified"
    CONFLICT = "conflict"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"
    UNSUPPORTED = "unsupported"


class VerificationResult(BaseModel):
    status: VerificationStatus
    method: str | None = None
    details_markdown: str | None = None
    confidence: float = Field(ge=0, le=1)


class ProblemResult(BaseModel):
    id: str
    number: str | None = None
    problem_type: str
    question_markdown: str
    solution_markdown: str
    answer_markdown: str
    verification: VerificationResult
    concepts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    needs_review: bool = False


class DocumentAnalysis(BaseModel):
    subject: str
    unit: str | None = None
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


class WorksheetResult(BaseModel):
    schema_version: int = 1
    document: DocumentAnalysis
    problems: list[ProblemResult]


class AnalyzeOptions(BaseModel):
    subject_hint: str | None = None
    language: str = "ko"


class InputFile(BaseModel):
    storage_key: str
    content_type: str
    original_filename: str


class VaultOperation(BaseModel):
    operation: str
    path: str
    content: str | None = None


class VaultChangeSet(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    base_revision: str | None = None
    operations: list[VaultOperation]
    requires_approval: bool = True
    reason: str


def utcnow() -> datetime:
    return datetime.now(UTC)
