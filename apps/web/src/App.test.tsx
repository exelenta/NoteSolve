import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

const resultPayload = {
  document_id: "doc-1",
  job_id: "job-1",
  provider: "fake",
  model: "notesolve-test",
  prompt_version: "v1",
  result: {
    schema_version: 1,
    document: { subject: "수학", unit: "이차방정식", confidence: 0.96, warnings: [] },
    problems: [{
      id: "problem-1",
      number: "1",
      problem_type: "short_answer",
      question_markdown: "$x^2=4$를 푸시오.",
      solution_markdown: "$x=\\pm 2$",
      answer_markdown: "$x=2, -2$",
      verification: { status: "verified", method: "대입 검산", details_markdown: null, confidence: 0.98 },
      concepts: ["이차방정식"],
      warnings: [],
      confidence: 0.95,
      needs_review: false,
    }],
  },
};

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
}

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/health")) {
        return new Response(JSON.stringify({ status: "ok", service: "notesolve-api", version: "0.1.0" }), { status: 200 });
      }
      if (url.endsWith("/documents") && init?.method === "POST") {
        return new Response(JSON.stringify({ document_id: "doc-1", job_id: "job-1", status: "ingested", duplicate: false }), { status: 201 });
      }
      if (url.endsWith("/jobs/job-1/analyze")) {
        return new Response(JSON.stringify({ job_id: "job-1", status: "analyzing" }), { status: 202 });
      }
      if (url.endsWith("/jobs/job-1")) {
        return new Response(JSON.stringify({
          job_id: "job-1", document_id: "doc-1", stage: "completed", progress: 100, error_code: null, error_message: null,
        }), { status: 200 });
      }
      if (url.endsWith("/documents/doc-1/result")) {
        return new Response(JSON.stringify(resultPayload), { status: 200 });
      }
      return new Response(null, { status: 404 });
    }));
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: vi.fn(() => "blob:preview") });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: vi.fn() });
  });

  afterEach(() => vi.unstubAllGlobals());

  it("uploads, analyzes, and displays a worksheet result", async () => {
    renderApp();
    const input = screen.getByLabelText(/프린트 사진 또는 PDF/) as HTMLInputElement;
    await userEvent.upload(input, new File(["image"], "worksheet.png", { type: "image/png" }));
    await userEvent.click(screen.getByRole("button", { name: "NoteSolve에 업로드" }));
    expect(await screen.findByText("업로드가 완료되었습니다.")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "분석 시작" }));
    expect(await screen.findByText("분석 완료")).toBeInTheDocument();
    expect((await screen.findAllByText(/이차방정식/)).length).toBeGreaterThan(0);
    expect(screen.getByText("$x=2, -2$")).toBeInTheDocument();
    expect(screen.getByText("검산 완료")).toBeInTheDocument();
  });

  it("rejects an unsupported file", async () => {
    renderApp();
    const input = screen.getByLabelText(/프린트 사진 또는 PDF/) as HTMLInputElement;
    await userEvent.upload(input, new File(["text"], "notes.txt", { type: "text/plain" }), { applyAccept: false });
    expect(await screen.findByText(/JPG, PNG 또는 PDF/)).toBeInTheDocument();
  });
});
