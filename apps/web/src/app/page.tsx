"use client";

import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { UploadDropzone } from "@/components/upload-dropzone";
import { uploadFiles } from "@/lib/api";

export default function HomePage() {
  const router = useRouter();
  const upload = useMutation({
    mutationFn: (files: File[]) => uploadFiles(files),
    onSuccess: ({ jobId }) => router.push(`/analyze/${jobId}`)
  });

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">Function Point Analysis</h1>
        <p className="mt-1 text-muted-foreground">
          Upload project files and get an IFPUG-style function point breakdown produced by a local LLM.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Upload</CardTitle>
          <CardDescription>
            Drag &amp; drop ZIPs, PDFs, source code, or docs. Up to 50 MB total.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <UploadDropzone
            submitting={upload.isPending}
            onSubmit={async (files) => {
              await upload.mutateAsync(files);
            }}
          />
        </CardContent>
      </Card>

      {upload.isError && (
        <Alert variant="destructive">
          <AlertTitle>Upload failed</AlertTitle>
          <AlertDescription>{(upload.error as Error).message}</AlertDescription>
        </Alert>
      )}
    </div>
  );
}
