"use client";

import * as React from "react";
import { useQuery } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { getJob, jobStreamUrl } from "@/lib/api";
import type { FpaResult, JobStatus } from "@/lib/types";

export interface JobProgressProps {
  jobId: string;
  onDone?: (result: FpaResult) => void;
}

type StreamState = {
  status: JobStatus;
  progress: number;
  message?: string;
  result?: FpaResult;
};

function useJobStream(jobId: string): StreamState & { sseFailed: boolean } {
  const [state, setState] = React.useState<StreamState>({ status: "pending", progress: 0 });
  const [sseFailed, setSseFailed] = React.useState(false);

  React.useEffect(() => {
    if (typeof window === "undefined" || typeof EventSource === "undefined") {
      setSseFailed(true);
      return;
    }
    let cancelled = false;
    let es: EventSource;
    try {
      es = new EventSource(jobStreamUrl(jobId));
    } catch {
      setSseFailed(true);
      return;
    }
    let reconnects = 0;

    const handleStatusEvent = (ev: MessageEvent) => {
      if (cancelled) return;
      try {
        const payload = JSON.parse(ev.data) as Partial<FpaResult> & { progress?: number };
        setState((prev) => ({
          status: (payload.status as JobStatus) ?? prev.status,
          progress: typeof payload.progress === "number" ? payload.progress : prev.progress,
          message: payload.message ?? prev.message,
          result: payload.status === "done" ? (payload as FpaResult) : prev.result
        }));
        if (payload.status === "done" || payload.status === "error") {
          es.close();
        }
      } catch {
        /* ignore malformed event */
      }
    };

    es.addEventListener("status", handleStatusEvent);

    es.onerror = () => {
      reconnects += 1;
      if (reconnects > 3) {
        es.close();
        setSseFailed(true);
      }
    };

    return () => {
      cancelled = true;
      es.close();
    };
  }, [jobId]);

  return { ...state, sseFailed };
}

export function JobProgress({ jobId, onDone }: JobProgressProps) {
  const stream = useJobStream(jobId);

  const polling = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    enabled: stream.sseFailed && stream.status !== "done" && stream.status !== "error",
    refetchInterval: (q) => {
      const data = q.state.data;
      if (data?.status === "done" || data?.status === "error") return false;
      return 1500;
    }
  });

  const effective: StreamState = stream.sseFailed && polling.data
    ? {
        status: polling.data.status,
        progress: polling.data.progress ?? 0,
        message: polling.data.message,
        result: polling.data.status === "done" ? polling.data : undefined
      }
    : stream;

  React.useEffect(() => {
    if (effective.status === "done" && effective.result && onDone) {
      onDone(effective.result);
    }
  }, [effective.status, effective.result, onDone]);

  if (effective.status === "error") {
    return (
      <Alert variant="destructive">
        <AlertTitle>Analysis failed</AlertTitle>
        <AlertDescription>{effective.message ?? "Unknown error"}</AlertDescription>
      </Alert>
    );
  }

  const label =
    effective.status === "done"
      ? "Done"
      : effective.status === "running"
      ? effective.message ?? "Analyzing…"
      : "Queued";

  return (
    <div className="flex flex-col gap-3" data-testid="job-progress">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {effective.status !== "done" && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
        <span>{label}</span>
        {stream.sseFailed && <span className="text-xs">(polling)</span>}
      </div>
      <Progress value={effective.progress || (effective.status === "done" ? 100 : 5)} />
    </div>
  );
}
