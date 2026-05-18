import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { FpaSummary } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface FPAResultCardProps {
  summary: FpaSummary;
  className?: string;
}

function MetricCell({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-md border p-4">
      <span className="text-xs uppercase tracking-wide text-muted-foreground">{label}</span>
      <span className="text-3xl font-semibold tabular-nums" data-testid={`metric-${label.toLowerCase()}`}>
        {value}
      </span>
      {hint && <span className="text-xs text-muted-foreground">{hint}</span>}
    </div>
  );
}

export function FPAResultCard({ summary, className }: FPAResultCardProps) {
  return (
    <Card className={cn("w-full", className)} data-testid="fpa-result-card">
      <CardHeader>
        <CardTitle>Function Point Analysis</CardTitle>
        <CardDescription>IFPUG summary metrics</CardDescription>
      </CardHeader>
      <CardContent className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <MetricCell label="UFP" value={summary.ufp.toString()} hint="Unadjusted Function Points" />
        <MetricCell label="VAF" value={summary.vaf.toFixed(2)} hint="Value Adjustment Factor" />
        <MetricCell label="AFP" value={summary.afp.toFixed(1)} hint="Adjusted Function Points" />
      </CardContent>
    </Card>
  );
}
