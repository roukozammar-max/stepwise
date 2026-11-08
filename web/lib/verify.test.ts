import { describe, expect, it } from "vitest";
import { checkableLines, linesNeedingCheck, mapResults, stepKey, type StepResult } from "./verify";

const board = (...latex: string[]) => latex.map((l, i) => ({ id: `id${i}`, latex: l }));

const step = (line: number, status: StepResult["status"], message = ""): StepResult => ({
  line,
  status,
  method: "",
  message,
  counterexample: null,
});

describe("checkableLines", () => {
  it("skips empty lines and compares each line with the previous non-empty one", () => {
    const items = checkableLines(board("a", "", "b", "  ", "c"));
    expect(items.map((i) => i.id)).toEqual(["id0", "id2", "id4"]);
    expect(items[0].isStart).toBe(true);
    expect(items[1].key).toBe(stepKey("a", "b"));
    expect(items[2].key).toBe(stepKey("b", "c"));
  });

  it("changing a line changes its own key and the next line's key", () => {
    const before = checkableLines(board("a", "b", "c"));
    const after = checkableLines(board("a", "B", "c"));
    expect(after[0].key).toBe(before[0].key);
    expect(after[1].key).not.toBe(before[1].key);
    expect(after[2].key).not.toBe(before[2].key);
  });
});

describe("mapResults", () => {
  it("matches answers to lines by position, skipping the starting point", () => {
    const items = checkableLines(board("a", "", "b", "c"));
    const verdicts = mapResults(items, [
      step(0, "start"),
      step(1, "correct"),
      step(2, "incorrect", "lost x = -2"),
    ]);
    expect(Object.keys(verdicts)).toEqual(["id2", "id3"]);
    expect(verdicts.id3).toEqual({ key: items[2].key, status: "incorrect", message: "lost x = -2" });
  });
});

describe("linesNeedingCheck", () => {
  it("only lists steps without an up-to-date verdict", () => {
    const items = checkableLines(board("a", "b", "c"));
    const verdicts = mapResults(items, [step(0, "start"), step(1, "correct"), step(2, "correct")]);
    expect(linesNeedingCheck(items, verdicts)).toEqual([]);

    const edited = checkableLines(board("a", "b", "C"));
    expect(linesNeedingCheck(edited, verdicts).map((i) => i.id)).toEqual(["id2"]);
  });
});
