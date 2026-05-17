import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FPAResultCard } from "@/components/fpa-result-card";
import { FunctionBreakdownTable } from "@/components/function-breakdown-table";
import { UploadDropzone } from "@/components/upload-dropzone";
import type { FpaFunction } from "@/lib/types";

describe("responsive utility classes", () => {
  it("FPAResultCard metric grid is mobile-first (1 col, 3 cols at sm)", () => {
    const { container } = render(<FPAResultCard summary={{ ufp: 10, vaf: 1, afp: 10 }} />);
    const grid = container.querySelector('[class*="grid-cols-1"]');
    expect(grid).toBeTruthy();
    expect(grid!.className).toMatch(/sm:grid-cols-3/);
  });

  it("FunctionBreakdownTable wraps in horizontal-scroll container", () => {
    const fns: FpaFunction[] = [
      { type: "EI", name: "x", complexity: "low", fp: 3, justification: "j" }
    ];
    const { container } = render(<FunctionBreakdownTable functions={fns} />);
    expect(container.querySelector('.overflow-auto')).toBeTruthy();
  });

  it("UploadDropzone footer wraps on narrow viewport", () => {
    render(<UploadDropzone onSubmit={() => undefined} />);
    const btn = screen.getByRole("button", { name: /^analyze$/i });
    const footer = btn.parentElement;
    expect(footer?.className).toMatch(/flex-wrap/);
  });
});
