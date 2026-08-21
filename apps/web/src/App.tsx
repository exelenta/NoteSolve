import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import ReactMarkdown from "react-markdown";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import {
  analyzeJob,
  applyVaultChangeSet,
  createVaultChangeSet,
  getAgentEditJob,
  getVaultChangeSet,
  getDocumentResult,
  getHealth,
  getJob,
  rollbackVaultChangeSet,
  requestAgentEdit,
  uploadDocument,
} from "./api";
import type { AnalyzeOptions, ContentBlock, ProblemResult } from "./api";
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

function DocumentBlock({ block }: { block: ContentBlock }) {
  return <article className="document-block">
    <div className="block-meta"><span>{block.kind.replaceAll("_", " ")}</span><span>p. {block.source_page}</span></div>
    <MarkdownContent>{block.markdown}</MarkdownContent>
    {block.answer_markdown && <div className="block-answer"><strong>답</strong><MarkdownContent>{block.answer_markdown}</MarkdownContent></div>}
    {block.explanation_markdown && <div className="block-help"><strong>학습 도움</strong><MarkdownContent>{block.explanation_markdown}</MarkdownContent></div>}
  </article>;
}

export function App() {
  const [files, setFiles] = useState<File[]>([]);
  const [subject, setSubject] = useState("");
  const [helpLevel, setHelpLevel] = useState<AnalyzeOptions["help_level"]>("concise");
  const [outputStyle, setOutputStyle] = useState<AnalyzeOptions["output_style"]>("source_faithful");
  const [customInstruction, setCustomInstruction] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const [analysisStarted, setAnalysisStarted] = useState(false);
  const [editInstruction, setEditInstruction] = useState("");
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
  const agentEdit = useMutation({
    mutationFn: ({ changeSetId, instruction }: { changeSetId: string; instruction: string }) =>
      requestAgentEdit(changeSetId, instruction),
  });
  const agentJob = useQuery({
    queryKey: ["agent-edit-job", agentEdit.data?.job_id],
    queryFn: () => getAgentEditJob(agentEdit.data!.job_id),
    enabled: Boolean(agentEdit.data?.job_id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "completed" || status === "failed" ? false : 1000;
    },
  });
  const agentProposal = useQuery({
    queryKey: ["vault-change-set", agentJob.data?.result_change_set_id],
    queryFn: () => getVaultChangeSet(agentJob.data!.result_change_set_id!),
    enabled: agentJob.data?.status === "completed" && Boolean(agentJob.data.result_change_set_id),
  });
  const proposalApply = useMutation({ mutationFn: applyVaultChangeSet });
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

  function selectFiles(candidates: File[]) {
    upload.reset();
    analysis.reset();
    vaultChangeSet.reset();
    vaultApply.reset();
    vaultRollback.reset();
    agentEdit.reset();
    proposalApply.reset();
    setEditInstruction("");
    setAnalysisStarted(false);
    if (!candidates.length) return;
    if (candidates.length > 30 || candidates.some((candidate) => !ACCEPTED_TYPES.includes(candidate.type))) {
      setFiles([]);
      setValidationError("JPG, PNG 또는 PDF 파일만 업로드할 수 있습니다.");
      return;
    }
    setValidationError(null);
    setFiles(candidates);
  }

  function handleFileInput(event: ChangeEvent<HTMLInputElement>) {
    selectFiles(Array.from(event.target.files ?? []));
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    selectFiles(Array.from(event.dataTransfer.files));
  }

  function startAnalysis() {
    if (!upload.data) return;
    analysis.reset();
    setAnalysisStarted(false);
    analysis.mutate({ jobId: upload.data.job_id, options: {
      subject_hint: subject.trim() || null, language: "ko", help_level: helpLevel,
      output_style: outputStyle, custom_instruction: customInstruction.trim() || null,
    }});
  }

  const progress = job.data?.progress ?? 0;
  const currentVaultChangeSet = vaultRollback.data ?? vaultApply.data ?? vaultChangeSet.data;

  return (
    <main className="shell">
      <header className="header">
        <div>
          <p className="eyebrow">DOCUMENT → KNOWLEDGE</p>
          <h1>NoteSolve</h1>
          <p className="subtitle">프린트의 구조는 살리고, 필요한 만큼만 도와주는 Obsidian 자동화.</p>
        </div>
        <span className={`status ${health.isSuccess ? "online" : "offline"}`}>
          {health.isPending ? "API 확인 중" : health.isSuccess ? "API 연결됨" : "API 연결 안 됨"}
        </span>
      </header>

      <section className="panel">
        <label className="dropzone" onDragOver={(event) => event.preventDefault()} onDrop={handleDrop}>
          <input multiple type="file" accept="image/jpeg,image/png,application/pdf" onChange={handleFileInput} />
          <span className="drop-icon">N</span>
          <span className="drop-title">여러 장의 프린트 또는 PDF를 놓으세요</span>
          <span className="drop-help">JPG · PNG · PDF · 최대 30개 · 선택 순서가 페이지 순서입니다</span>
          <span className="button-like">페이지 선택</span>
        </label>

        {validationError && <p className="message error">{validationError}</p>}
        {files.length > 0 && (
          <div className="selection-stack">
            <div className="page-strip">{files.map((file, index) => <div className="page-chip" key={`${file.name}-${index}`}><b>{index + 1}</b><span>{file.name}</span></div>)}</div>
            <div className="options-grid">
              <label><span>과목</span><input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="자동 인식 (또는 직접 입력)" /></label>
              <label><span>학습 도움</span><select value={helpLevel} onChange={(e) => setHelpLevel(e.target.value as AnalyzeOptions["help_level"])}><option value="none">원문 정리만</option><option value="answers">답만 채우기</option><option value="concise">간단한 설명</option><option value="detailed">자세한 설명</option></select></label>
              <label><span>정리 방식</span><select value={outputStyle} onChange={(e) => setOutputStyle(e.target.value as AnalyzeOptions["output_style"])}><option value="source_faithful">원본 구조 유지</option><option value="study_notes">학습 노트</option><option value="summary">핵심 요약</option></select></label>
              <label className="wide"><span>추가 요청</span><input value={customInstruction} onChange={(e) => setCustomInstruction(e.target.value)} placeholder="예: 영어 문장은 원문과 번역을 함께 표시" /></label>
            </div>
            <div className="upload-cta"><span><b>{files.length}개 페이지</b> · {(files.reduce((sum, f) => sum + f.size, 0) / 1024 / 1024).toFixed(2)} MB</span>
              <button disabled={upload.isPending} onClick={() => upload.mutate(files)}>
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
              <p>문서 유형과 과목을 인식해 원본 구조에 맞는 학습 노트를 만듭니다.</p>
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
                  <p className="section-kicker">STUDY DOCUMENT</p>
                  <h2>{result.data.result.document.title ?? result.data.result.document.subject}</h2>
                  <p>{result.data.result.document.subject} · {result.data.result.document.unit ?? "단원 미분류"} · 블록 {result.data.result.blocks.length}개</p>
                </div>
                <dl>
                  <div><dt>문서 신뢰도</dt><dd>{Math.round(result.data.result.document.confidence * 100)}%</dd></div>
                  <div><dt>분석 모델</dt><dd>{result.data.model}</dd></div>
                  <div><dt>사용 토큰</dt><dd>{result.data.usage.total_tokens.toLocaleString()}</dd></div>
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
              {currentVaultChangeSet?.status === "applied" && (
                <div className="panel agent-panel">
                  <p className="section-kicker">AI NOTE EDITOR</p>
                  <h2>노트 수정 요청</h2>
                  <p className="agent-help">AI는 Vault를 직접 수정하지 않고 승인 가능한 변경안만 제안합니다.</p>
                  <textarea
                    value={editInstruction}
                    onChange={(event) => setEditInstruction(event.target.value)}
                    placeholder="예: 문제 1의 풀이를 더 자세히 설명하고 핵심 공식을 마지막에 정리해줘"
                    maxLength={4000}
                  />
                  <button
                    disabled={agentEdit.isPending || !editInstruction.trim()}
                    onClick={() => agentEdit.mutate({
                      changeSetId: currentVaultChangeSet.change_set.id,
                      instruction: editInstruction,
                    })}
                  >
                    {agentEdit.isPending ? "수정 요청 전송 중…" : "AI 변경안 만들기"}
                  </button>
                  {agentEdit.isError && <p className="message error">{agentEdit.error.message}</p>}
                  {agentJob.data && agentJob.data.status !== "completed" && agentJob.data.status !== "failed" && (
                    <p className="agent-status">AI가 노트를 수정하고 있습니다…</p>
                  )}
                  {agentJob.data?.status === "failed" && (
                    <p className="message error">{agentJob.data.error_message ?? "AI 수정에 실패했습니다."}</p>
                  )}
                  {agentJob.data?.status === "completed" && (
                    <p className="agent-status">
                      수정안 생성 완료 · {agentJob.data.usage.total_tokens.toLocaleString()} tokens
                    </p>
                  )}
                </div>
              )}
              {agentProposal.data && (
                <div className="panel agent-proposal">
                  <div className="section-heading">
                    <div>
                      <p className="section-kicker">AI EDIT PROPOSAL</p>
                      <h2>AI 수정 변경안</h2>
                    </div>
                    <span className={`approval-badge ${proposalApply.data?.status ?? agentProposal.data.status}`}>
                      {proposalApply.data?.status === "applied" ? "Vault 반영됨" : "승인 필요"}
                    </span>
                  </div>
                  <p>{agentProposal.data.change_set.reason}</p>
                  <p className="vault-path">{agentProposal.data.change_set.operations[0]?.path}</p>
                  <pre>{agentProposal.data.change_set.operations[0]?.content}</pre>
                  {!proposalApply.data && (
                    <div className="vault-actions">
                      <button
                        disabled={proposalApply.isPending}
                        onClick={() => proposalApply.mutate(agentProposal.data.change_set.id)}
                      >
                        {proposalApply.isPending ? "수정 반영 중…" : "AI 수정안 승인"}
                      </button>
                    </div>
                  )}
                  {proposalApply.isError && <p className="message error">{proposalApply.error.message}</p>}
                </div>
              )}
              {result.data.result.document.warnings.length > 0 && (
                <div className="document-warnings">문서 검토 필요: {result.data.result.document.warnings.join(" · ")}</div>
              )}
              <div className="document-flow">
                {result.data.result.blocks.length > 0
                  ? result.data.result.blocks.map((block) => <DocumentBlock key={block.id} block={block} />)
                  : result.data.result.problems.map((problem) => <ProblemCard key={problem.id} problem={problem} />)}
              </div>
            </>
          )}
        </section>
      )}
    </main>
  );
}
