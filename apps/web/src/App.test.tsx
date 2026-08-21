import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={client}><App /></QueryClientProvider>);
}

describe("App", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).endsWith("/health")) {
        return new Response(JSON.stringify({ status: "ok", service: "notesolve-api", version: "0.1.0" }), { status: 200 });
      }
      return new Response(JSON.stringify({ document_id: "doc-1", job_id: "job-1", status: "ingested", duplicate: false }), { status: 201 });
    }));
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:preview"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => vi.unstubAllGlobals());

  it("uploads a supported worksheet", async () => {
    renderApp();
    const input = screen.getByLabelText(/프린트 사진 또는 PDF/) as HTMLInputElement;
    await userEvent.upload(input, new File(["image"], "worksheet.png", { type: "image/png" }));
    await userEvent.click(screen.getByRole("button", { name: "NoteSolve에 업로드" }));
    expect(await screen.findByText("업로드가 완료되었습니다.")).toBeInTheDocument();
    expect(screen.getByText("doc-1")).toBeInTheDocument();
  });

  it("rejects an unsupported file", async () => {
    renderApp();
    const input = screen.getByLabelText(/프린트 사진 또는 PDF/) as HTMLInputElement;
    await userEvent.upload(input, new File(["text"], "notes.txt", { type: "text/plain" }), { applyAccept: false });
    expect(await screen.findByText(/JPG, PNG 또는 PDF/)).toBeInTheDocument();
  });
});
