import hashlib
import re
from collections.abc import AsyncIterator
from pathlib import Path
from uuid import UUID


class LocalStorageProvider:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    async def save(
        self,
        *,
        workspace_id: UUID,
        document_id: UUID,
        filename: str,
        chunks: AsyncIterator[bytes],
    ) -> tuple[str, str, int]:
        suffix = Path(filename).suffix.lower()
        safe_suffix = suffix if re.fullmatch(r"\.[a-z0-9]{1,8}", suffix) else ".bin"
        storage_key = f"workspaces/{workspace_id}/documents/{document_id}/original{safe_suffix}"
        target = (self.root / storage_key).resolve()
        if self.root not in target.parents:
            raise ValueError("Unsafe storage path")
        target.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()
        size = 0
        with target.open("wb") as output:
            async for chunk in chunks:
                digest.update(chunk)
                size += len(chunk)
                output.write(chunk)
        return storage_key, digest.hexdigest(), size

    async def read(self, storage_key: str) -> bytes:
        target = (self.root / storage_key).resolve()
        if self.root not in target.parents:
            raise ValueError("Unsafe storage path")
        return target.read_bytes()

    def delete(self, storage_key: str) -> None:
        target = (self.root / storage_key).resolve()
        if self.root not in target.parents:
            raise ValueError("Unsafe storage path")
        target.unlink(missing_ok=True)
