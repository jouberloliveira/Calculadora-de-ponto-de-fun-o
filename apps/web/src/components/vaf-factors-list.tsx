import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import type { VafFactor } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface VAFFactorsListProps {
  factors: VafFactor[];
  className?: string;
}

export function VAFFactorsList({ factors, className }: VAFFactorsListProps) {
  if (!factors || factors.length === 0) return null;
  return (
    <Card className={cn("w-full", className)} data-testid="vaf-factors-list">
      <CardHeader>
        <CardTitle>VAF factors</CardTitle>
        <CardDescription>14 General System Characteristics</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {factors.map((f, i) => (
            <li key={`${f.name}-${i}`} className="rounded-md border p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium">{f.name}</span>
                <span className="inline-flex h-7 min-w-[1.75rem] items-center justify-center rounded-md bg-secondary px-2 text-sm font-semibold tabular-nums">
                  {f.value}
                </span>
              </div>
              {f.rationale && <p className="mt-1 text-xs text-muted-foreground">{f.rationale}</p>}
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
