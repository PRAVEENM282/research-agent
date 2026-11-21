import { describe, expect, it } from "vitest";
import { getPipelineStep } from "./taskPipelineStep";

describe("task pipeline status", () => {
  it("stops at human review before approval and advances after resume", () => {
    expect(getPipelineStep("AWAITING_APPROVAL")).toBe(2);
    expect(getPipelineStep("RESUMED")).toBe(3);
    expect(getPipelineStep("COMPLETED")).toBe(4);
  });
});
