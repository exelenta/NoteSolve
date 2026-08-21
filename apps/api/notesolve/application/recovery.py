from sqlalchemy import select
from sqlalchemy.orm import Session

from notesolve.domain.models import AgentEditJobStatus, DocumentStatus, PipelineStage
from notesolve.infrastructure.tables import AgentEditJobRow, DocumentRow, PipelineJobRow


def mark_interrupted_jobs_failed(session: Session) -> int:
    recovered = 0
    active_stages = {
        PipelineStage.ANALYZING,
        PipelineStage.VALIDATING,
        PipelineStage.VERIFYING,
        PipelineStage.FORMATTING,
        PipelineStage.VAULT_PREVIEW,
    }
    jobs = session.scalars(
        select(PipelineJobRow).where(PipelineJobRow.stage.in_(active_stages))
    ).all()
    for job in jobs:
        job.stage = PipelineStage.FAILED
        job.error_code = "process_interrupted"
        job.error_message = "Server restarted while the analysis job was running"
        document = session.get(DocumentRow, job.document_id)
        if document is not None:
            document.status = DocumentStatus.FAILED
        recovered += 1

    agent_jobs = session.scalars(
        select(AgentEditJobRow).where(
            AgentEditJobRow.status.in_({
                AgentEditJobStatus.QUEUED,
                AgentEditJobStatus.RUNNING,
            })
        )
    ).all()
    for agent_job in agent_jobs:
        agent_job.status = AgentEditJobStatus.FAILED
        agent_job.error_message = "Server restarted while the AI edit job was running"
        recovered += 1
    session.commit()
    return recovered
