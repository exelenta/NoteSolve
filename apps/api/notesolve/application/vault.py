from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from notesolve.application.markdown import build_vault_preview
from notesolve.domain.models import (
    LOCAL_WORKSPACE_ID,
    VaultChangeSet,
    VaultChangeSetStatus,
    VaultOperation,
    WorksheetResult,
    utcnow,
)
from notesolve.domain.ports import VaultRepository
from notesolve.infrastructure.local_vault import VaultConflictError
from notesolve.infrastructure.tables import (
    DocumentRow,
    VaultChangeSetRow,
    VaultRevisionRow,
    WorksheetResultRow,
)


class VaultChangeSetService:
    def __init__(self, *, session: Session, vault: VaultRepository) -> None:
        self._session = session
        self._vault = vault

    def create(self, document_id: UUID) -> VaultChangeSetRow:
        document = self._session.get(DocumentRow, document_id)
        if document is None:
            raise LookupError("Document not found")
        result_row = self._session.scalar(
            select(WorksheetResultRow).where(WorksheetResultRow.document_id == document_id)
        )
        if result_row is None:
            raise RuntimeError("Document analysis is not complete")
        preview = build_vault_preview(
            document_id=document_id,
            original_filename=document.original_filename,
            result=WorksheetResult.model_validate(result_row.result_json),
        )
        operation = self._single_write_operation(preview)
        row = VaultChangeSetRow(
            id=preview.id,
            workspace_id=LOCAL_WORKSPACE_ID,
            document_id=document_id,
            status=VaultChangeSetStatus.PENDING,
            base_revision=self._vault.revision(operation.path),
            operations_json=[item.model_dump(mode="json") for item in preview.operations],
            reason=preview.reason,
        )
        self._session.add(row)
        self._session.commit()
        return row

    def get(self, change_set_id: UUID) -> VaultChangeSetRow:
        row = self._session.get(VaultChangeSetRow, change_set_id)
        if row is None:
            raise LookupError("Vault ChangeSet not found")
        return row

    def apply(self, change_set_id: UUID) -> VaultChangeSetRow:
        row = self.get(change_set_id)
        if row.status != VaultChangeSetStatus.PENDING:
            raise RuntimeError(f"ChangeSet cannot be applied from status {row.status}")
        change_set = self.to_domain(row)
        operation = self._single_write_operation(change_set)
        if operation.content is None:
            raise ValueError("Vault write operation requires content")
        try:
            previous_content = self._vault.write(
                operation.path,
                operation.content,
                row.base_revision,
            )
        except VaultConflictError as exc:
            row.status = VaultChangeSetStatus.CONFLICT
            row.error_message = str(exc)
            self._session.commit()
            raise
        self._session.add(VaultRevisionRow(
            id=uuid4(),
            change_set_id=row.id,
            path=operation.path,
            previous_content=previous_content,
            applied_content_hash=self._vault.content_hash(operation.content),
        ))
        row.status = VaultChangeSetStatus.APPLIED
        row.applied_at = utcnow()
        row.error_message = None
        self._session.commit()
        return row

    def rollback(self, change_set_id: UUID) -> VaultChangeSetRow:
        row = self.get(change_set_id)
        if row.status != VaultChangeSetStatus.APPLIED:
            raise RuntimeError(f"ChangeSet cannot be rolled back from status {row.status}")
        revision = self._session.scalar(
            select(VaultRevisionRow).where(VaultRevisionRow.change_set_id == row.id)
        )
        if revision is None:
            raise RuntimeError("Vault revision is missing")
        try:
            self._vault.restore(
                revision.path,
                revision.previous_content,
                revision.applied_content_hash,
            )
        except VaultConflictError as exc:
            row.status = VaultChangeSetStatus.CONFLICT
            row.error_message = str(exc)
            self._session.commit()
            raise
        row.status = VaultChangeSetStatus.ROLLED_BACK
        row.error_message = None
        self._session.commit()
        return row

    @staticmethod
    def to_domain(row: VaultChangeSetRow) -> VaultChangeSet:
        return VaultChangeSet(
            id=row.id,
            base_revision=row.base_revision,
            operations=[
                VaultOperation.model_validate(operation) for operation in row.operations_json
            ],
            requires_approval=True,
            reason=row.reason,
        )

    @staticmethod
    def _single_write_operation(change_set: VaultChangeSet) -> VaultOperation:
        if (
            len(change_set.operations) != 1
            or change_set.operations[0].operation not in {"create", "update"}
        ):
            raise ValueError("Exactly one create or update operation is required")
        return change_set.operations[0]
