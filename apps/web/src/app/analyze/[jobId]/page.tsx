"use client";

import * as React from "react";
import Link from "next/link";
import { JobProgress } from "@/components/job-progress";
import { FPAResultCard } from "@/components/fpa-result-card";
import { FunctionBreakdownTable } from "@/components/function-breakdown-table";
import { VAFFactorsList } from "@/components/vaf-factors-list";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { FpaResult } from "@/lib/types";

export default function AnalyzePage({ params }: { params: { jobId: string } }) {
  const [result, setResult] = React.useState<FpaResult | null>(null);

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight sm:text-2xl">Analysis</h1>
          <p className="break-all text-xs text-muted-foreground">
            Job <span className="font-mono">{params.jobId}</span>
          </p>
        </div>
        <Button asChild variant="outline">
          <Link href="/">New analysis</Link>
        </Button>
      </div>

      {!result && (
        <Card>
          <CardHeader>
            <CardTitle>Progress</CardTitle>
          </CardHeader>
          <CardContent>
            <JobProgress jobId={params.jobId} onDone={setResult} />
          </CardContent>
        </Card>
      )}

      {result?.summary && <FPAResultCard summary={result.summary} />}
      {result?.functions && result.functions.length > 0 && (
        <FunctionBreakdownTable functions={result.functions} />
      )}
      {result?.vafFactors && result.vafFactors.length > 0 && (
        <VAFFactorsList factors={result.vafFactors} />
      )}
    </div>
  );
}
