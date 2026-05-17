"use client";

import * as React from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { type FpaFunction, type FunctionType, FUNCTION_TYPE_LABELS, FUNCTION_TYPE_ORDER } from "@/lib/types";
import { cn } from "@/lib/utils";

export interface FunctionBreakdownTableProps {
  functions: FpaFunction[];
  className?: string;
}

function groupByType(functions: FpaFunction[]): Record<FunctionType, FpaFunction[]> {
  const groups = {
    EI: [], EO: [], EQ: [], ILF: [], EIF: []
  } as Record<FunctionType, FpaFunction[]>;
  for (const f of functions) groups[f.type].push(f);
  return groups;
}

function ComplexityBadge({ complexity }: { complexity: FpaFunction["complexity"] }) {
  const styles = {
    low: "bg-emerald-100 text-emerald-900",
    medium: "bg-amber-100 text-amber-900",
    high: "bg-rose-100 text-rose-900"
  } as const;
  return (
    <span className={cn("inline-flex rounded-full px-2 py-0.5 text-xs font-medium capitalize", styles[complexity])}>
      {complexity}
    </span>
  );
}

function Row({ fn }: { fn: FpaFunction }) {
  const [expanded, setExpanded] = React.useState(false);
  return (
    <>
      <TableRow data-testid="function-row">
        <TableCell className="w-8">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label={expanded ? "Collapse justification" : "Expand justification"}
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          </Button>
        </TableCell>
        <TableCell className="font-medium">{fn.name}</TableCell>
        <TableCell>
          <ComplexityBadge complexity={fn.complexity} />
        </TableCell>
        <TableCell className="text-right tabular-nums">{fn.fp}</TableCell>
      </TableRow>
      {expanded && (
        <TableRow>
          <TableCell />
          <TableCell colSpan={3} className="bg-muted/40 text-sm text-muted-foreground">
            {fn.justification}
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

export function FunctionBreakdownTable({ functions, className }: FunctionBreakdownTableProps) {
  const groups = groupByType(functions);

  return (
    <Card className={cn("w-full", className)} data-testid="function-breakdown-table">
      <CardHeader>
        <CardTitle>Function breakdown</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-6">
        {FUNCTION_TYPE_ORDER.map((type) => {
          const items = groups[type];
          if (items.length === 0) return null;
          const subtotal = items.reduce((acc, f) => acc + f.fp, 0);
          return (
            <section key={type} data-testid={`group-${type}`} aria-labelledby={`group-${type}-heading`}>
              <header className="mb-2 flex items-baseline justify-between">
                <h3 id={`group-${type}-heading`} className="text-sm font-semibold">
                  <span className="mr-2 inline-flex rounded bg-secondary px-2 py-0.5 font-mono text-xs">{type}</span>
                  {FUNCTION_TYPE_LABELS[type]}
                </h3>
                <span className="text-xs text-muted-foreground">
                  {items.length} item{items.length === 1 ? "" : "s"} · {subtotal} FP
                </span>
              </header>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-8" />
                    <TableHead>Name</TableHead>
                    <TableHead>Complexity</TableHead>
                    <TableHead className="text-right">FP</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((fn, i) => (
                    <Row key={`${type}-${i}-${fn.name}`} fn={fn} />
                  ))}
                </TableBody>
              </Table>
            </section>
          );
        })}
      </CardContent>
    </Card>
  );
}
