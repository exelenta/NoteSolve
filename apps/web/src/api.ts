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

