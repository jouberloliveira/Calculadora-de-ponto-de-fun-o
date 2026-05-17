import type { FpaResult } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const MAX_TOTAL_BYTES = 50 * 1024 * 1024;

export const ACCEPTED_MIME: Record<string, string[]> = {
  "application/zip": [".zip"],
  "application/x-zip-compressed": [".zip"],
  "application/pdf": [".pdf"],
  "text/plain": [".txt", ".md"],
  "text/markdown": [".md"],
  "text/x-python": [".py"],
  "application/javascript": [".js"],
  "application/typescript": [".ts"],
  "text/javascript": [".js"],
  "text/typescript": [".ts"],
  "application/json": [".json"],
  "text/csv": [".csv"]
};

export const ACCEPTED_EXTENSIONS = Array.from(
  new Set(Object.values(ACCEPTED_MIME).flat())
);

export function validateFiles(files: File[]): { ok: true } | { ok: false; error: string } {
  if (files.length === 0) return { ok: false, error: "No files selected." };
  const total = files.reduce((acc, f) => acc + f.size, 0);
  if (total > MAX_TOTAL_BYTES) {
    return { ok: false, error: `Total size exceeds 50 MB (${(total / 1024 / 1024).toFixed(1)} MB).` };
  }
  for (const f of files) {
    if (!isAcceptedFile(f)) {
      return { ok: false, error: `Unsupported file type: ${f.name}` };
    }
  }
  return { ok: true };
}

export function isAcceptedFile(file: File): boolean {
  if (file.type && ACCEPTED_MIME[file.type]) return true;
  const lower = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export async function uploadFiles(files: File[]): Promise<{ jobId: string }> {
  const form = new FormData();
  for (const f of files) form.append("files", f, f.name);
  const res = await fetch(`${API_URL}/analyze`, { method: "POST", body: form });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`Upload failed: ${res.status} ${text}`);
  }
  return res.json();
}

export async function getJob(jobId: string): Promise<FpaResult> {
  const res = await fetch(`${API_URL}/analyze/${jobId}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Job fetch failed: ${res.status}`);
  return res.json();
}

export function jobStreamUrl(jobId: string): string {
  return `${API_URL}/analyze/${jobId}/stream`;
}

export const MAX_UPLOAD_BYTES = MAX_TOTAL_BYTES;
