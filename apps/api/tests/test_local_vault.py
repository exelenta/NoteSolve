from pathlib import Path

import pytest
from notesolve.infrastructure.local_vault import LocalVaultRepository


def test_local_vault_rejects_parent_traversal(tmp_path: Path) -> None:
    vault = LocalVaultRepository(tmp_path / "vault")
    with pytest.raises(ValueError, match="Unsafe Vault path"):
        vault.write("../outside.md", "unsafe", None)
