from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from notesolve.application.vault import VaultChangeSetService
from notesolve.domain.models import (
    LOCAL_WORKSPACE_ID,
    AgentEditJobStatus,
    VaultChangeSetStatus,
    VaultOperation,
)
from notesolve.domain.ports import VaultNoteEditor, VaultRepository
from notesolve.infrastructure.tables import AgentEditJobRow, VaultChangeSetRow


class AgentEditService:
    def __init__(
        self,
        *,
        session: Session,
        vault: VaultRepository,
        editor: VaultNoteEditor,
    ) -> None:
        self._session = session
        self._vault = vault
        self._editor = editor

    def create_job(self, source_change_set_id: UUID, instruction: str) -> AgentEditJobRow:
        source = self._session.get(VaultChangeSetRow, source_change_set_id)
        if source is None:
            raise LookupError("Source Vault ChangeSet not found")
        if source.status != VaultChangeSetStatus.APPLIED:
            raise RuntimeError("AI edits require an applied Vault ChangeSet")
        normalized = instruction.strip()
        if not normalized:
            raise ValueError("Edit instruction cannot be empty")
        if len(normalized) > 4000:
            raise ValueError("Edit instruction is too long")
        job = AgentEditJobRow(
            id=uuid4(),
            workspace_id=LOCAL_WORKSPACE_ID,
            source_change_set_id=source_change_set_id,
            status=AgentEditJobStatus.QUEUED,
            instruction=normalized,
        )
        self._session.add(job)
        self._session.commit()
        return job

    async def run(self, job_id: UUID) -> None:
        job = self.get_job(job_id)
        job.status = AgentEditJobStatus.RUNNING
        self._session.commit()
        try:
            source = self._session.get(VaultChangeSetRow, job.source_change_set_id)
            if source is None or source.status != VaultChangeSetStatus.APPLIED:
                raise RuntimeError("Source Vault ChangeSet is no longer applied")
            source_change_set = VaultChangeSetService.to_domain(source)
            operation = VaultChangeSetService._single_write_operation(source_change_set)
            current_content = self._vault.read(operation.path)
            if current_content is None:
                raise RuntimeError("Vault note no longer exists")
            proposal = await self._editor.edit(
                current_content=current_content,
                instruction=job.instruction,
            )
            if proposal.content == current_content:
                raise RuntimeError("AI edit did not change the note")
            change_set = VaultChangeSetRow(
                id=uuid4(),
                workspace_id=source.workspace_id,
                document_id=source.document_id,
                status=VaultChangeSetStatus.PENDING,
                base_revision=self._vault.content_hash(current_content),
                operations_json=[VaultOperation(
                    operation="update",
                    path=operation.path,
                    content=proposal.content,
                ).model_dump(mode="json")],
                reason=proposal.summary,
            )
            self._session.add(change_set)
            self._session.flush()
            job.result_change_set_id = change_set.id
            job.status = AgentEditJobStatus.COMPLETED
            job.error_message = None
            self._session.commit()
        except Exception as exc:
            self._session.rollback()
            job = self.get_job(job_id)
            job.status = AgentEditJobStatus.FAILED
            job.error_message = str(exc)[:1000]
            self._session.commit()
            raise

    def get_job(self, job_id: UUID) -> AgentEditJobRow:
        job = self._session.get(AgentEditJobRow, job_id)
        if job is None:
            raise LookupError("Agent edit job not found")
        return job
