"use client";

import * as React from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { UploadCloud, X, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { ACCEPTED_MIME, MAX_UPLOAD_BYTES, validateFiles } from "@/lib/api";
import { cn, formatBytes } from "@/lib/utils";

export interface UploadDropzoneProps {
  onSubmit: (files: File[]) => void | Promise<void>;
  submitting?: boolean;
  className?: string;
}

export function UploadDropzone({ onSubmit, submitting = false, className }: UploadDropzoneProps) {
  const [files, setFiles] = React.useState<File[]>([]);
  const [error, setError] = React.useState<string | null>(null);

  const onDrop = React.useCallback(
    (accepted: File[], rejected: FileRejection[]) => {
      if (rejected.length > 0) {
        const first = rejected[0];
        const reason = first.errors[0]?.message ?? "Rejected";
        setError(`${first.file.name}: ${reason}`);
      } else {
        setError(null);
      }
      if (accepted.length === 0) return;
      const merged = [...files, ...accepted];
      const result = validateFiles(merged);
      if (!result.ok) {
        setError(result.error);
        return;
      }
      setFiles(merged);
    },
    [files]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED_MIME,
    maxSize: MAX_UPLOAD_BYTES,
    multiple: true
  });

  const totalBytes = files.reduce((acc, f) => acc + f.size, 0);

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index));
    setError(null);
  }

  async function handleSubmit() {
    const result = validateFiles(files);
    if (!result.ok) {
      setError(result.error);
      return;
    }
    await onSubmit(files);
  }

  return (
    <div className={cn("flex flex-col gap-4", className)}>
      <div
        {...getRootProps()}
        data-testid="dropzone"
        className={cn(
          "flex flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed border-input bg-background p-6 text-center cursor-pointer transition-colors hover:bg-accent/40 sm:p-8",
          isDragActive && "border-primary bg-accent/60"
        )}
      >
        <input {...getInputProps()} aria-label="File upload" />
        <UploadCloud className="h-10 w-10 text-muted-foreground" aria-hidden />
        <div className="space-y-1">
          <p className="text-sm font-medium">
            {isDragActive ? "Drop the files here" : "Drag & drop project files, or click to browse"}
          </p>
          <p className="text-xs text-muted-foreground">
            ZIP, PDF, source code, text. Up to 50 MB total.
          </p>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" role="alert">
          <AlertTitle>Upload error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {files.length > 0 && (
        <ul className="divide-y rounded-md border" data-testid="file-list">
          {files.map((f, i) => (
            <li key={`${f.name}-${i}`} className="flex items-center justify-between gap-3 px-3 py-2">
              <div className="flex min-w-0 items-center gap-2">
                <FileText className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                <span className="truncate text-sm" title={f.name}>{f.name}</span>
                <span className="text-xs text-muted-foreground">{formatBytes(f.size)}</span>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                aria-label={`Remove ${f.name}`}
                onClick={() => removeFile(i)}
              >
                <X className="h-4 w-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-muted-foreground" aria-live="polite">
          {files.length === 0
            ? "No files selected"
            : `${files.length} file${files.length === 1 ? "" : "s"} · ${formatBytes(totalBytes)}`}
        </p>
        <Button onClick={handleSubmit} disabled={files.length === 0 || submitting}>
          {submitting ? "Uploading…" : "Analyze"}
        </Button>
      </div>
    </div>
  );
}
