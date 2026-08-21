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
