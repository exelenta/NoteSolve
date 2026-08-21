import hashlib
import os
import tempfile
from pathlib import Path, PurePosixPath


class VaultConflictError(Exception):
    pass


class LocalVaultRepository:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def read(self, path: str) -> str | None:
        target = self._target(path)
        return target.read_text(encoding="utf-8") if target.exists() else None

    def revision(self, path: str) -> str | None:
        content = self.read(path)
        return self.content_hash(content) if content is not None else None

    def write(self, path: str, content: str, expected_revision: str | None) -> str | None:
        target = self._target(path)
        current = self.read(path)
        current_revision = self.content_hash(current) if current is not None else None
        if current_revision != expected_revision:
            raise VaultConflictError("Vault file changed after the preview was created")
        target.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(target, content)
        return current

    def restore(self, path: str, previous_content: str | None, expected_hash: str) -> None:
        target = self._target(path)
        current = self.read(path)
        if current is None or self.content_hash(current) != expected_hash:
            raise VaultConflictError(
                "Applied Vault file has changed and cannot be rolled back safely"
            )
        if previous_content is None:
            target.unlink()
            self._remove_empty_parents(target.parent)
        else:
            self._atomic_write(target, previous_content)

    @staticmethod
    def content_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _target(self, path: str) -> Path:
        portable = PurePosixPath(path)
        if portable.is_absolute() or ".." in portable.parts:
            raise ValueError("Unsafe Vault path")
        target = self.root.joinpath(*portable.parts).resolve()
        if target != self.root and self.root not in target.parents:
            raise ValueError("Unsafe Vault path")
        return target

    @staticmethod
    def _atomic_write(target: Path, content: str) -> None:
        handle, temporary_name = tempfile.mkstemp(
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
        )
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as output:
                output.write(content)
            os.replace(temporary_name, target)
        finally:
            Path(temporary_name).unlink(missing_ok=True)

    def _remove_empty_parents(self, directory: Path) -> None:
        while directory != self.root:
            try:
                directory.rmdir()
            except OSError:
                break
            directory = directory.parent
