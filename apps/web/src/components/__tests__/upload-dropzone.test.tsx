import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UploadDropzone } from "@/components/upload-dropzone";

function makeFile(name: string, sizeBytes: number, type: string): File {
  const blob = new Blob([new Uint8Array(sizeBytes)], { type });
  return new File([blob], name, { type });
}

function dropOn(dropzone: HTMLElement, files: File[]) {
  const data = {
    dataTransfer: {
      files,
      items: files.map((f) => ({ kind: "file", type: f.type, getAsFile: () => f })),
      types: ["Files"]
    }
  };
  fireEvent.drop(dropzone, data);
}

describe("UploadDropzone", () => {
  it("rejects unsupported MIME type", async () => {
    const onSubmit = vi.fn();
    render(<UploadDropzone onSubmit={onSubmit} />);

    const dz = screen.getByTestId("dropzone");
    dropOn(dz, [makeFile("evil.exe", 1024, "application/x-msdownload")]);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.queryByTestId("file-list")).not.toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("rejects files exceeding total size cap", async () => {
    const onSubmit = vi.fn();
    render(<UploadDropzone onSubmit={onSubmit} />);

    const dz = screen.getByTestId("dropzone");
    dropOn(dz, [makeFile("huge.zip", 51 * 1024 * 1024, "application/zip")]);

    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("accepts valid files and submits them", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn();
    render(<UploadDropzone onSubmit={onSubmit} />);

    const dz = screen.getByTestId("dropzone");
    dropOn(dz, [makeFile("project.zip", 2048, "application/zip")]);

    await waitFor(() => expect(screen.getByTestId("file-list")).toBeInTheDocument());
    expect(screen.getByText("project.zip")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^analyze$/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0][0].name).toBe("project.zip");
  });
});
