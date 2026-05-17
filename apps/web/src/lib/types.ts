export type FunctionType = "EI" | "EO" | "EQ" | "ILF" | "EIF";
export type Complexity = "low" | "medium" | "high";
export type JobStatus = "pending" | "running" | "done" | "error";

export interface FpaFunction {
  type: FunctionType;
  name: string;
  complexity: Complexity;
  fp: number;
  justification: string;
}

export interface VafFactor {
  name: string;
  value: number;
  rationale?: string;
}

export interface FpaSummary {
  ufp: number;
  vaf: number;
  afp: number;
}

export interface FpaResult {
  jobId: string;
  status: JobStatus;
  progress?: number;
  message?: string;
  summary?: FpaSummary;
  functions?: FpaFunction[];
  vafFactors?: VafFactor[];
  error?: string;
}

export const FUNCTION_TYPE_LABELS: Record<FunctionType, string> = {
  EI: "External Inputs",
  EO: "External Outputs",
  EQ: "External Inquiries",
  ILF: "Internal Logical Files",
  EIF: "External Interface Files"
};

export const FUNCTION_TYPE_ORDER: FunctionType[] = ["EI", "EO", "EQ", "ILF", "EIF"];
