from collections.abc import AsyncIterator, Sequence
from typing import Protocol
from uuid import UUID

from notesolve.domain.models import (
    AnalyzeOptions,
    InputFile,
    VaultChangeSet,
    VaultOperation,
    WorksheetResult,
)


class WorksheetAnalyzer(Protocol):
    async def analyze(
        self, files: Sequence[InputFile], options: AnalyzeOptions
    ) -> WorksheetResult: ...


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
    async def preview_changes(
        self, changes: Sequence[VaultOperation], reason: str
    ) -> VaultChangeSet: ...

    async def apply_changes(self, change_set_id: UUID) -> None: ...

    async def rollback(self, revision_id: UUID) -> None: ...
