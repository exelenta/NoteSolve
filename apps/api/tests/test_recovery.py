from uuid import uuid4

from notesolve.application.recovery import mark_interrupted_jobs_failed
from notesolve.domain.models import (
    LOCAL_WORKSPACE_ID,
    AgentEditJobStatus,
    DocumentStatus,
    PipelineStage,
    VaultChangeSetStatus,
)
from notesolve.infrastructure.db import Base
from notesolve.infrastructure.tables import (
    AgentEditJobRow,
    DocumentRow,
    PipelineJobRow,
    VaultChangeSetRow,
)
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def test_marks_interrupted_background_jobs_as_failed() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    document_id, pipeline_job_id, change_set_id, edit_job_id = (
        uuid4(), uuid4(), uuid4(), uuid4()
    )
    with Session(engine) as session:
        session.add(DocumentRow(
            id=document_id,
            workspace_id=LOCAL_WORKSPACE_ID,
            original_filename="worksheet.png",
            content_type="image/png",
            storage_key="worksheet.png",
            content_hash="recovery",
            size_bytes=1,
            status=DocumentStatus.PROCESSING,
        ))
        session.add(PipelineJobRow(
            id=pipeline_job_id,
            workspace_id=LOCAL_WORKSPACE_ID,
            document_id=document_id,
            stage=PipelineStage.ANALYZING,
            progress=10,
        ))
        session.add(VaultChangeSetRow(
            id=change_set_id,
            workspace_id=LOCAL_WORKSPACE_ID,
            document_id=document_id,
            status=VaultChangeSetStatus.APPLIED,
            operations_json=[],
            reason="test",
        ))
        session.add(AgentEditJobRow(
            id=edit_job_id,
            workspace_id=LOCAL_WORKSPACE_ID,
            source_change_set_id=change_set_id,
            status=AgentEditJobStatus.RUNNING,
            instruction="test",
        ))
        session.commit()

        assert mark_interrupted_jobs_failed(session) == 2
        assert session.get(PipelineJobRow, pipeline_job_id).stage == PipelineStage.FAILED
        assert session.get(AgentEditJobRow, edit_job_id).status == AgentEditJobStatus.FAILED
