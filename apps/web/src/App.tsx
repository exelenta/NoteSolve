import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import {
  analyzeJob,
  applyVaultChangeSet,
  createVaultChangeSet,
  getDocumentResult,
  getHealth,
  getJob,
  rollbackVaultChangeSet,
  uploadDocument,
} from "./api";
import type { ProblemResult } from "./api";
import "katex/dist/katex.min.css";
import "./styles.css";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "application/pdf"];
const STAGE_LABELS = {
  ingested: "업로드 완료",
  analyzing: "문제 인식 및 풀이 중",
  validating: "응답 구조 검사 중",
  verifying: "풀이 검산 중",
  formatting: "학습 노트 정리 중",
  vault_preview: "Vault 저장 준비 중",
  completed: "분석 완료",
  failed: "분석 실패",
};
const VERIFICATION_LABELS = {
  self_checked: "AI 자체 검산",
  verified: "독립 검산 완료",
  conflict: "검산 불일치",
  manual_review_required: "수동 검토 필요",
  unsupported: "검산 미지원",
};

function MarkdownContent({ children }: { children: string }) {
  return (
    <div className="markdown-content">
      <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {children}
      </ReactMarkdown>
    </div>
  );
}

function ProblemCard({ problem }: { problem: ProblemResult }) {
  const needsAttention = problem.needs_review || problem.confidence < 0.9;
  return (
    <article className={`problem-card ${needsAttention ? "attention" : ""}`}>
      <header className="problem-header">
        <div>
          <span className="problem-number">문제 {problem.number ?? "—"}</span>
          <span className="problem-type">{problem.problem_type}</span>
        </div>
        <span className={`confidence ${needsAttention ? "low" : "high"}`}>
          신뢰도 {Math.round(problem.confidence * 100)}%
        </span>
      </header>

      {problem.warnings.length > 0 && (
        <div className="warning-box">검토 필요: {problem.warnings.join(" · ")}</div>
      )}
      <section className="result-section">
        <h3>문제</h3>
        <MarkdownContent>{problem.question_markdown}</MarkdownContent>
      </section>
      <section className="result-section">
        <h3>풀이</h3>
        <MarkdownContent>{problem.solution_markdown}</MarkdownContent>
      </section>
      <section className="result-section answer-section">
        <h3>정답</h3>
        <MarkdownContent>{problem.answer_markdown}</MarkdownContent>
      </section>
      <footer className="verification">
        <span className={`verification-badge ${problem.verification.status}`}>
          {VERIFICATION_LABELS[problem.verification.status]}
        </span>
        <span>{problem.verification.method ?? "AI 자체 검산"}</span>
        <span>신뢰도 {Math.round(problem.verification.confidence * 100)}%</span>
      </footer>
      {problem.verification.details_markdown && (
        <div className="verification-details">
          <MarkdownContent>{problem.verification.details_markdown}</MarkdownContent>
        </div>
      )}
      {problem.concepts.length > 0 && (
        <div className="concepts">{problem.concepts.map((concept) => <span key={concept}>#{concept}</span>)}</div>
      )}
    </article>
  );
}

export function App() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [analysisStarted, setAnalysisStarted] = useState(false);
  const health = useQuery({ queryKey: ["health"], queryFn: getHealth, retry: false });
  const upload = useMutation({
    mutationFn: uploadDocument,
    onSuccess: () => setAnalysisStarted(false),
  });
  const analysis = useMutation({
    mutationFn: analyzeJob,
    onSuccess: () => setAnalysisStarted(true),
  });
  const vaultChangeSet = useMutation({ mutationFn: createVaultChangeSet });
  const vaultApply = useMutation({ mutationFn: applyVaultChangeSet });
  const vaultRollback = useMutation({ mutationFn: rollbackVaultChangeSet });
  const job = useQuery({
    queryKey: ["job", upload.data?.job_id],
    queryFn: () => getJob(upload.data!.job_id),
    enabled: analysisStarted && Boolean(upload.data),
    refetchInterval: (query) => {
      const status = query.state.data?.stage;
      return status === "completed" || status === "failed" ? false : 1000;
    },
  });
  const result = useQuery({
    queryKey: ["result", upload.data?.document_id],
    queryFn: () => getDocumentResult(upload.data!.document_id),
    enabled: job.data?.stage === "completed" && Boolean(upload.data),
  });

  useEffect(() => {
    if (!file || !file.type.startsWith("image/")) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function selectFile(candidate: File | undefined) {
    upload.reset();
    analysis.reset();
    vaultChangeSet.reset();
    vaultApply.reset();
    vaultRollback.reset();
    setAnalysisStarted(false);
    if (!candidate) return;
    if (!ACCEPTED_TYPES.includes(candidate.type)) {
      setFile(null);
      setValidationError("JPG, PNG 또는 PDF 파일만 업로드할 수 있습니다.");
      return;
    }
    setValidationError(null);
    setFile(candidate);
  }

  function handleFileInput(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0]);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    selectFile(event.dataTransfer.files[0]);
  }

  function startAnalysis() {
    if (!upload.data) return;
    analysis.reset();
    setAnalysisStarted(false);
    analysis.mutate(upload.data.job_id);
  }

  const progress = job.data?.progress ?? 0;
  const currentVaultChangeSet = vaultRollback.data ?? vaultApply.data ?? vaultChangeSet.data;

  return (
    <main className="shell">
      <header className="header">
        <div>
          <p className="eyebrow">AI WORKSHEET COMPANION</p>
          <h1>NoteSolve</h1>
          <p className="subtitle">사진 한 장을 검토 가능한 학습 노트로 바꿉니다.</p>
        </div>
        <span className={`status ${health.isSuccess ? "online" : "offline"}`}>
          {health.isPending ? "API 확인 중" : health.isSuccess ? "API 연결됨" : "API 연결 안 됨"}
        </span>
      </header>

      <section className="panel">
        <label className="dropzone" onDragOver={(event) => event.preventDefault()} onDrop={handleDrop}>
          <input type="file" accept="image/jpeg,image/png,application/pdf" onChange={handleFileInput} />
          <span className="drop-title">프린트 사진 또는 PDF를 여기에 놓으세요</span>
          <span className="drop-help">JPG · PNG · PDF</span>
          <span className="button-like">파일 선택</span>
        </label>

        {validationError && <p className="message error">{validationError}</p>}
        {file && (
          <div className="selection">
            {previewUrl ? <img src={previewUrl} alt="선택한 프린트 미리보기" /> : <div className="pdf">PDF</div>}
            <div>
              <p className="filename">{file.name}</p>
              <p className="meta">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
              <button disabled={upload.isPending} onClick={() => upload.mutate(file)}>
                {upload.isPending ? "업로드 중…" : "NoteSolve에 업로드"}
              </button>
            </div>
          </div>
        )}

        {upload.isError && <p className="message error">{upload.error.message}</p>}
        {upload.isSuccess && (
          <div className="upload-result" role="status">
            <div>
              <strong>{upload.data.duplicate ? "이미 등록된 문서입니다." : "업로드가 완료되었습니다."}</strong>
              <p>AI가 문제 인식, 풀이와 검산을 한 번에 수행합니다.</p>
            </div>
            <button disabled={analysis.isPending || (analysisStarted && job.data?.stage !== "failed")} onClick={startAnalysis}>
              {analysis.isPending ? "분석 요청 중…" : "분석 시작"}
            </button>
          </div>
        )}
        {analysis.isError && <p className="message error">{analysis.error.message}</p>}
      </section>

      {analysisStarted && (
        <section className="panel progress-panel" aria-live="polite">
          <div className="section-heading">
            <div>
              <p className="section-kicker">AI ANALYSIS</p>
              <h2>{job.data ? STAGE_LABELS[job.data.stage] : "분석 준비 중"}</h2>
            </div>
            <strong>{progress}%</strong>
          </div>
          <div className="progress-track"><div style={{ width: `${progress}%` }} /></div>
          {job.isError && <p className="message error">{job.error.message}</p>}
          {job.data?.stage === "failed" && (
            <div className="failure-box">
              <p><strong>분석을 완료하지 못했습니다.</strong><br />{job.data.error_message ?? "잠시 후 다시 시도해 주세요."}</p>
              <button onClick={startAnalysis}>다시 분석</button>
            </div>
          )}
        </section>
      )}

      {job.data?.stage === "completed" && (
        <section className="results-area">
          {result.isPending && <div className="panel loading-result">분석 결과를 정리하고 있습니다…</div>}
          {result.isError && <p className="panel message error">{result.error.message}</p>}
          {result.data && (
            <>
              <div className="panel results-summary">
                <div>
                  <p className="section-kicker">WORKSHEET RESULT</p>
                  <h2>{result.data.result.document.subject}</h2>
                  <p>{result.data.result.document.unit ?? "단원 미분류"} · 문제 {result.data.result.problems.length}개</p>
                </div>
                <dl>
                  <div><dt>문서 신뢰도</dt><dd>{Math.round(result.data.result.document.confidence * 100)}%</dd></div>
                  <div><dt>분석 모델</dt><dd>{result.data.model}</dd></div>
                </dl>
                <button
                  className="secondary-button"
                  disabled={vaultChangeSet.isPending}
                  onClick={() => vaultChangeSet.mutate(result.data.document_id)}
                >
                  {vaultChangeSet.isPending ? "변경안 저장 중…" : "Obsidian 노트 미리보기"}
                </button>
              </div>
              {vaultChangeSet.isError && <p className="panel message error">{vaultChangeSet.error.message}</p>}
              {currentVaultChangeSet && (
                <div className="panel vault-preview">
                  <div className="section-heading">
                    <div>
                      <p className="section-kicker">VAULT CHANGESET · {currentVaultChangeSet.status}</p>
                      <h2>생성될 Obsidian 노트</h2>
                    </div>
                    <span className={`approval-badge ${currentVaultChangeSet.status}`}>
                      {currentVaultChangeSet.status === "pending" && "승인 필요"}
                      {currentVaultChangeSet.status === "applied" && "Vault 반영됨"}
                      {currentVaultChangeSet.status === "rolled_back" && "롤백 완료"}
                      {currentVaultChangeSet.status === "conflict" && "충돌 발생"}
                    </span>
                  </div>
                  <p className="vault-path">{currentVaultChangeSet.change_set.operations[0]?.path}</p>
                  <pre>{currentVaultChangeSet.change_set.operations[0]?.content}</pre>
                  <div className="vault-actions">
                    {currentVaultChangeSet.status === "pending" && (
                      <button
                        disabled={vaultApply.isPending}
                        onClick={() => vaultApply.mutate(currentVaultChangeSet.change_set.id)}
                      >
                        {vaultApply.isPending ? "Vault 반영 중…" : "승인하고 Vault에 반영"}
                      </button>
                    )}
                    {currentVaultChangeSet.status === "applied" && (
                      <button
                        className="danger-button"
                        disabled={vaultRollback.isPending}
                        onClick={() => vaultRollback.mutate(currentVaultChangeSet.change_set.id)}
                      >
                        {vaultRollback.isPending ? "롤백 중…" : "변경사항 롤백"}
                      </button>
                    )}
                  </div>
                  {vaultApply.isError && <p className="message error">{vaultApply.error.message}</p>}
                  {vaultRollback.isError && <p className="message error">{vaultRollback.error.message}</p>}
                </div>
              )}
              {result.data.result.document.warnings.length > 0 && (
                <div className="document-warnings">문서 검토 필요: {result.data.result.document.warnings.join(" · ")}</div>
              )}
              <div className="problem-list">
                {result.data.result.problems.map((problem) => <ProblemCard key={problem.id} problem={problem} />)}
              </div>
            </>
          )}
        </section>
      )}
    </main>
  );
}
