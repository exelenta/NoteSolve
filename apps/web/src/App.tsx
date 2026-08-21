import { useMutation, useQuery } from "@tanstack/react-query";
import { ChangeEvent, DragEvent, useEffect, useState } from "react";
import { getHealth, uploadDocument } from "./api";
import "./styles.css";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "application/pdf"];

export function App() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const health = useQuery({ queryKey: ["health"], queryFn: getHealth, retry: false });
  const upload = useMutation({ mutationFn: uploadDocument });

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
          <div className="result" role="status">
            <strong>{upload.data.duplicate ? "이미 등록된 문서입니다." : "업로드가 완료되었습니다."}</strong>
            <dl>
              <div><dt>Document</dt><dd>{upload.data.document_id}</dd></div>
              <div><dt>Job</dt><dd>{upload.data.job_id}</dd></div>
              <div><dt>Status</dt><dd>{upload.data.status}</dd></div>
            </dl>
          </div>
        )}
      </section>
    </main>
  );
}

