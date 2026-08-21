const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface CreateDocumentResponse {
  document_id: string;
  job_id: string;
  status: string;
  duplicate: boolean;
}

export interface AnalyzeJobResponse {
  job_id: string;
  status: string;
}

export type PipelineStage =
  | "ingested"
  | "analyzing"
  | "validating"
  | "verifying"
  | "formatting"
  | "vault_preview"
  | "completed"
  | "failed";

export interface JobStatusResponse {
  job_id: string;
  document_id: string;
  stage: PipelineStage;
  progress: number;
  error_code: string | null;
  error_message: string | null;
}

export interface VerificationResult {
  status: "self_checked" | "verified" | "conflict" | "manual_review_required" | "unsupported";
  method: string | null;
  details_markdown: string | null;
  confidence: number;
}

export interface ProblemResult {
  id: string;
  number: string | null;
  problem_type: string;
  question_markdown: string;
  solution_markdown: string;
  answer_markdown: string;
  verification: VerificationResult;
  concepts: string[];
  warnings: string[];
  confidence: number;
  needs_review: boolean;
}

export interface WorksheetResultResponse {
  document_id: string;
  job_id: string;
  provider: string;
  model: string;
  prompt_version: string;
  result: {
    schema_version: number;
    document: {
      subject: string;
      unit: string | null;
      confidence: number;
      warnings: string[];
    };
    problems: ProblemResult[];
  };
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
}

export interface VaultPreviewResponse {
  document_id: string;
  change_set: {
    id: string;
    base_revision: string | null;
    requires_approval: boolean;
    reason: string;
    operations: Array<{
      operation: string;
      path: string;
      content: string | null;
    }>;
  };
}

export type VaultChangeSetStatus = "pending" | "applied" | "conflict" | "rolled_back";

export interface VaultChangeSetResponse extends VaultPreviewResponse {
  status: VaultChangeSetStatus;
  error_message: string | null;
}

export interface AgentEditJobResponse {
  job_id: string;
  status: "queued" | "running" | "completed" | "failed";
  result_change_set_id: string | null;
  error_message: string | null;
  usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_BASE_URL}/health`);
  if (!response.ok) throw new Error("API에 연결할 수 없습니다.");
  return response.json() as Promise<HealthResponse>;
}

export async function uploadDocument(file: File): Promise<CreateDocumentResponse> {
  const body = new FormData();
  body.append("file", file);
  const response = await fetch(`${API_BASE_URL}/documents`, { method: "POST", body });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "업로드에 실패했습니다.");
  }
  return response.json() as Promise<CreateDocumentResponse>;
}

export async function analyzeJob(jobId: string): Promise<AnalyzeJobResponse> {
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/analyze`, { method: "POST" });
  if (!response.ok) throw new Error("분석 작업을 시작하지 못했습니다.");
  return response.json() as Promise<AnalyzeJobResponse>;
}

export async function getJob(jobId: string): Promise<JobStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/jobs/${jobId}`);
  if (!response.ok) throw new Error("작업 상태를 불러오지 못했습니다.");
  return response.json() as Promise<JobStatusResponse>;
}

export async function getDocumentResult(documentId: string): Promise<WorksheetResultResponse> {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}/result`);
  if (!response.ok) throw new Error("분석 결과를 불러오지 못했습니다.");
  return response.json() as Promise<WorksheetResultResponse>;
}

export async function getVaultPreview(documentId: string): Promise<VaultPreviewResponse> {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}/vault-preview`);
  if (!response.ok) throw new Error("Obsidian 노트 미리보기를 만들지 못했습니다.");
  return response.json() as Promise<VaultPreviewResponse>;
}

export async function createVaultChangeSet(documentId: string): Promise<VaultChangeSetResponse> {
  const response = await fetch(`${API_BASE_URL}/documents/${documentId}/vault-change-sets`, {
    method: "POST",
  });
  if (!response.ok) throw new Error("Vault 변경안을 저장하지 못했습니다.");
  return response.json() as Promise<VaultChangeSetResponse>;
}

export async function applyVaultChangeSet(changeSetId: string): Promise<VaultChangeSetResponse> {
  const response = await fetch(`${API_BASE_URL}/vault-change-sets/${changeSetId}/apply`, {
    method: "POST",
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "Vault 반영에 실패했습니다.");
  }
  return response.json() as Promise<VaultChangeSetResponse>;
}

export async function rollbackVaultChangeSet(changeSetId: string): Promise<VaultChangeSetResponse> {
  const response = await fetch(`${API_BASE_URL}/vault-change-sets/${changeSetId}/rollback`, {
    method: "POST",
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "Vault 롤백에 실패했습니다.");
  }
  return response.json() as Promise<VaultChangeSetResponse>;
}

export async function requestAgentEdit(
  changeSetId: string,
  instruction: string,
): Promise<AgentEditJobResponse> {
  const response = await fetch(`${API_BASE_URL}/vault-change-sets/${changeSetId}/edit-proposals`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ instruction }),
  });
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(payload?.detail ?? "AI 수정 요청을 시작하지 못했습니다.");
  }
  return response.json() as Promise<AgentEditJobResponse>;
}

export async function getAgentEditJob(jobId: string): Promise<AgentEditJobResponse> {
  const response = await fetch(`${API_BASE_URL}/agent-edit-jobs/${jobId}`);
  if (!response.ok) throw new Error("AI 수정 작업 상태를 불러오지 못했습니다.");
  return response.json() as Promise<AgentEditJobResponse>;
}

export async function getVaultChangeSet(changeSetId: string): Promise<VaultChangeSetResponse> {
  const response = await fetch(`${API_BASE_URL}/vault-change-sets/${changeSetId}`);
  if (!response.ok) throw new Error("AI 수정 변경안을 불러오지 못했습니다.");
  return response.json() as Promise<VaultChangeSetResponse>;
}
