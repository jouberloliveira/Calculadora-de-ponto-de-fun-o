import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { FunctionBreakdownTable } from "@/components/function-breakdown-table";
import type { FpaFunction } from "@/lib/types";

const sample: FpaFunction[] = [
  { type: "EI", name: "Create User", complexity: "low", fp: 3, justification: "form input" },
  { type: "EI", name: "Update User", complexity: "medium", fp: 4, justification: "form input" },
  { type: "EO", name: "Sales Report", complexity: "high", fp: 7, justification: "aggregation" },
  { type: "ILF", name: "Users", complexity: "low", fp: 7, justification: "table" }
];

describe("FunctionBreakdownTable", () => {
  it("groups rows by function type", () => {
    render(<FunctionBreakdownTable functions={sample} />);

    const eiGroup = screen.getByTestId("group-EI");
    expect(within(eiGroup).getByText("Create User")).toBeInTheDocument();
    expect(within(eiGroup).getByText("Update User")).toBeInTheDocument();
    expect(within(eiGroup).queryByText("Sales Report")).not.toBeInTheDocument();

    const eoGroup = screen.getByTestId("group-EO");
    expect(within(eoGroup).getByText("Sales Report")).toBeInTheDocument();

    const ilfGroup = screen.getByTestId("group-ILF");
    expect(within(ilfGroup).getByText("Users")).toBeInTheDocument();

    expect(screen.queryByTestId("group-EQ")).not.toBeInTheDocument();
    expect(screen.queryByTestId("group-EIF")).not.toBeInTheDocument();
  });
});
