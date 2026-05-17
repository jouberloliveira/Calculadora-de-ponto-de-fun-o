import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FPAResultCard } from "@/components/fpa-result-card";

describe("FPAResultCard", () => {
  it("renders UFP, VAF, and AFP from summary", () => {
    render(<FPAResultCard summary={{ ufp: 158, vaf: 1.05, afp: 165.9 }} />);
    expect(screen.getByTestId("metric-ufp")).toHaveTextContent("158");
    expect(screen.getByTestId("metric-vaf")).toHaveTextContent("1.05");
    expect(screen.getByTestId("metric-afp")).toHaveTextContent("165.9");
  });
});
