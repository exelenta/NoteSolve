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


class DocumentKind(StrEnum):
    WORKSHEET = "worksheet"
    NOTES = "notes"
    FILL_IN_THE_BLANK = "fill_in_the_blank"
    REFERENCE = "reference"
    MIXED = "mixed"


class ContentBlockKind(StrEnum):
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    TABLE = "table"
    DEFINITION = "definition"
    EXAMPLE = "example"
    EXERCISE = "exercise"
    FILL_IN_THE_BLANK = "fill_in_the_blank"
    QUOTE = "quote"
    CALLOUT = "callout"


class HelpLevel(StrEnum):
    NONE = "none"
    ANSWERS = "answers"
    CONCISE = "concise"
    DETAILED = "detailed"


class OutputStyle(StrEnum):
    SOURCE_FAITHFUL = "source_faithful"
    STUDY_NOTES = "study_notes"
    SUMMARY = "summary"


class VaultChangeSetStatus(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    CONFLICT = "conflict"
    ROLLED_BACK = "rolled_back"


class AgentEditJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


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
    title: str | None = None
    kind: DocumentKind = DocumentKind.WORKSHEET
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


class WorksheetResult(BaseModel):
    schema_version: int = 2
    document: DocumentAnalysis
    blocks: list["ContentBlock"] = Field(default_factory=list)
    problems: list[ProblemResult] = Field(default_factory=list)


class ContentBlock(BaseModel):
    id: str
    kind: ContentBlockKind
    source_page: int = Field(ge=1)
    heading_level: int | None = Field(default=None, ge=1, le=6)
    markdown: str
    answer_markdown: str | None = None
    explanation_markdown: str | None = None
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


class AnalyzeOptions(BaseModel):
    subject_hint: str | None = None
    language: str = "ko"
    help_level: HelpLevel = HelpLevel.CONCISE
    output_style: OutputStyle = OutputStyle.SOURCE_FAITHFUL
    custom_instruction: str | None = Field(default=None, max_length=2000)


class InputFile(BaseModel):
    storage_key: str
    content_type: str
    original_filename: str
    content: bytes


class AnalysisRecord(BaseModel):
    document_id: UUID
    job_id: UUID
    provider: str
    model: str
    prompt_version: str
    result: WorksheetResult
    created_at: datetime


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


class NoteEditProposal(BaseModel):
    content: str = Field(min_length=1, max_length=500_000)
    summary: str = Field(min_length=1, max_length=500)


def utcnow() -> datetime:
    return datetime.now(UTC)
