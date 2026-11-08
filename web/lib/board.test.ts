import { describe, expect, it } from "vitest";
import {
  MAX_LINES,
  STORAGE_KEY,
  boardAsLatex,
  boardReducer,
  loadBoard,
  saveBoard,
  starterBoard,
  type Line,
} from "./board";

const lines = (...latex: string[]): Line[] => latex.map((l, i) => ({ id: `id${i}`, latex: l }));

function memoryStorage(initial: Record<string, string> = {}) {
  const data = { ...initial };
  return {
    data,
    getItem: (k: string) => data[k] ?? null,
    setItem: (k: string, v: string) => {
      data[k] = v;
    },
  };
}

describe("boardReducer", () => {
  it("inserts a line directly below the given one", () => {
    const out = boardReducer(lines("a", "b"), { type: "insertAfter", id: "id0", newId: "new" });
    expect(out.map((l) => l.id)).toEqual(["id0", "new", "id1"]);
    expect(out[1].latex).toBe("");
  });

  it("never grows past the line limit", () => {
    const full = lines(...Array.from({ length: MAX_LINES }, (_, i) => `x+${i}`));
    expect(boardReducer(full, { type: "append", newId: "n" })).toHaveLength(MAX_LINES);
    expect(boardReducer(full, { type: "insertAfter", id: "id3", newId: "n" })).toHaveLength(
      MAX_LINES,
    );
  });

  it("keeps one empty line when the last line is deleted", () => {
    const out = boardReducer(lines("a"), { type: "delete", id: "id0" });
    expect(out).toEqual([{ id: "id0", latex: "" }]);
  });

  it("updates only the edited line", () => {
    const out = boardReducer(lines("a", "b"), { type: "update", id: "id1", latex: "c" });
    expect(out.map((l) => l.latex)).toEqual(["a", "c"]);
  });

  it("clear leaves a single empty line", () => {
    expect(boardReducer(lines("a", "b"), { type: "clear", newId: "z" })).toEqual([
      { id: "z", latex: "" },
    ]);
  });
});

describe("saving", () => {
  it("round-trips through storage", () => {
    const storage = memoryStorage();
    saveBoard(storage, lines("x^2", "2x"));
    expect(loadBoard(storage)).toEqual(lines("x^2", "2x"));
  });

  it("ignores missing, broken or old-format data", () => {
    expect(loadBoard(memoryStorage())).toBeNull();
    expect(loadBoard(memoryStorage({ [STORAGE_KEY]: "not json" }))).toBeNull();
    expect(loadBoard(memoryStorage({ [STORAGE_KEY]: '{"version":2,"lines":[]}' }))).toBeNull();
  });

  it("starts with the three-line example", () => {
    let n = 0;
    const board = starterBoard(() => `s${n++}`);
    expect(board).toHaveLength(3);
    expect(new Set(board.map((l) => l.id)).size).toBe(3);
  });
});

describe("boardAsLatex", () => {
  it("joins non-empty lines with newlines", () => {
    expect(boardAsLatex(lines("a", " ", "b "))).toBe("a\nb");
  });
});
