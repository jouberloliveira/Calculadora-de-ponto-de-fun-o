import * as React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { JobProgress } from "@/components/job-progress";
import type { FpaResult } from "@/lib/types";

type Listener = (ev: MessageEvent) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  readyState = 0;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  private listeners: Record<string, Listener[]> = {};

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: Listener) {
    (this.listeners[type] ||= []).push(listener);
  }

  removeEventListener(type: string, listener: Listener) {
    this.listeners[type] = (this.listeners[type] ?? []).filter((l) => l !== listener);
  }

  emit(type: string, data: unknown) {
    const ev = new MessageEvent(type, { data: JSON.stringify(data) });
    if (type === "message" && this.onmessage) this.onmessage(ev);
    (this.listeners[type] ?? []).forEach((l) => l(ev));
  }

  triggerError() {
    this.onerror?.(new Event("error"));
  }

  close() {
    this.readyState = 2;
  }
}

function renderWithClient(ui: React.ReactElement) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0, staleTime: 0 }
    }
  });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

const originalEventSource = (globalThis as any).EventSource;
const originalFetch = globalThis.fetch;

beforeEach(() => {
  MockEventSource.instances = [];
  (globalThis as any).EventSource = MockEventSource;
});

afterEach(() => {
  (globalThis as any).EventSource = originalEventSource;
  globalThis.fetch = originalFetch;
  vi.restoreAllMocks();
});

describe("JobProgress", () => {
  it("shows pending state initially", () => {
    renderWithClient(<JobProgress jobId="job-1" />);
    expect(screen.getByTestId("job-progress")).toBeInTheDocument();
    expect(screen.getByText(/queued/i)).toBeInTheDocument();
  });

  it("renders done state and fires onDone with result from SSE message", async () => {
    const onDone = vi.fn();
    renderWithClient(<JobProgress jobId="job-2" onDone={onDone} />);

    const es = MockEventSource.instances[0];
    expect(es).toBeTruthy();

    const result: FpaResult = {
      jobId: "job-2",
      status: "done",
      progress: 100,
      summary: { ufp: 10, vaf: 1, afp: 10 },
      functions: [],
      vafFactors: []
    };

    act(() => {
      es.emit("message", result);
    });

    await waitFor(() => expect(screen.getByText(/done/i)).toBeInTheDocument());
    expect(onDone).toHaveBeenCalledWith(expect.objectContaining({ jobId: "job-2", status: "done" }));
  });

  it("renders SSE error state with message", async () => {
    renderWithClient(<JobProgress jobId="job-3" />);
    const es = MockEventSource.instances[0];

    act(() => {
      es.emit("message", { status: "error", message: "Worker exploded" });
    });

    expect(await screen.findByTestId("job-progress-error")).toHaveTextContent(/worker exploded/i);
  });

  it("falls back to polling and surfaces polling.error when fetch keeps failing", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error("network down"));

    renderWithClient(<JobProgress jobId="job-4" />);
    const es = MockEventSource.instances[0];

    act(() => {
      for (let n = 0; n < 4; n++) es.triggerError();
    });

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalled());
    const errorAlert = await screen.findByTestId("job-progress-error");
    expect(errorAlert).toHaveTextContent(/job fetch failed/i);
  });
});
