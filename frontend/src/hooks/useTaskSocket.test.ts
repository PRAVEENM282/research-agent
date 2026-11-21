import { describe, expect, it } from "vitest";
import type { TaskStatus } from "../api/types";

const terminal = (status: TaskStatus) => ["COMPLETED", "FAILED", "REJECTED"].includes(status);

describe("task socket terminal state", () => {
  it("closes live updates for all terminal outcomes", () => {
    expect(terminal("COMPLETED")).toBe(true);
    expect(terminal("FAILED")).toBe(true);
    expect(terminal("REJECTED")).toBe(true);
    expect(terminal("AWAITING_APPROVAL")).toBe(false);
  });
});
