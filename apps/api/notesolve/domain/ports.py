from collections.abc import AsyncIterator, Sequence
from typing import Protocol
from uuid import UUID

from notesolve.domain.models import (
    AnalyzeOptions,
    InputFile,
    ProblemResult,
    VerificationResult,
    WorksheetResult,
)


class WorksheetAnalyzer(Protocol):
    async def analyze(
        self, files: Sequence[InputFile], options: AnalyzeOptions
    ) -> WorksheetResult: ...


class WorksheetVerifier(Protocol):
    async def verify(
        self,
        files: Sequence[InputFile],
        problem: ProblemResult,
        options: AnalyzeOptions,
    ) -> VerificationResult: ...


class StorageProvider(Protocol):
    async def save(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        filename: str,
        chunks: AsyncIterator[bytes],
    ) -> tuple[str, str, int]: ...

    async def read(self, storage_key: str) -> bytes: ...


class JobRunner(Protocol):
    async def enqueue_analysis(self, document_id: UUID) -> UUID: ...


class VaultRepository(Protocol):
    def read(self, path: str) -> str | None: ...

    def revision(self, path: str) -> str | None: ...

    def write(self, path: str, content: str, expected_revision: str | None) -> str | None: ...

    def restore(self, path: str, previous_content: str | None, expected_hash: str) -> None: ...

    def content_hash(self, content: str) -> str: ...
