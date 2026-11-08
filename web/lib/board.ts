/**
 * The board: an ordered list of lines, the actions that change it, and
 * saving it in the browser. Pure functions only, so they are easy to test.
 */

export type Line = { id: string; latex: string };

export const MAX_LINES = 50; // same limit as the API
export const STORAGE_KEY = "stepwise.board.v1";

export const STARTER_LINES: readonly string[] = [
  "\\frac{d}{dx}\\sin(x^2)",
  "=\\cos(x^2)\\cdot2x",
  "=\\cos(x^2)",
];

export function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function starterBoard(makeId: () => string = newId): Line[] {
  return STARTER_LINES.map((latex) => ({ id: makeId(), latex }));
}

export type BoardAction =
  | { type: "update"; id: string; latex: string }
  | { type: "insertAfter"; id: string; newId: string }
  | { type: "append"; newId: string }
  | { type: "delete"; id: string }
  | { type: "clear"; newId: string };

/** Apply one editing action. The board always keeps at least one line. */
export function boardReducer(lines: Line[], action: BoardAction): Line[] {
  switch (action.type) {
    case "update":
      return lines.map((l) => (l.id === action.id ? { ...l, latex: action.latex } : l));
    case "insertAfter": {
      if (lines.length >= MAX_LINES) return lines;
      const i = lines.findIndex((l) => l.id === action.id);
      if (i === -1) return lines;
      return [...lines.slice(0, i + 1), { id: action.newId, latex: "" }, ...lines.slice(i + 1)];
    }
    case "append":
      if (lines.length >= MAX_LINES) return lines;
      return [...lines, { id: action.newId, latex: "" }];
    case "delete": {
      const rest = lines.filter((l) => l.id !== action.id);
      return rest.length > 0 ? rest : [{ id: action.id, latex: "" }];
    }
    case "clear":
      return [{ id: action.newId, latex: "" }];
  }
}

type SavedBoard = { version: 1; lines: Line[] };

/** Read the saved board. Returns null if nothing usable is saved. */
export function loadBoard(storage: Pick<Storage, "getItem">): Line[] | null {
  let raw: string | null;
  try {
    raw = storage.getItem(STORAGE_KEY);
  } catch {
    return null; // storage blocked (private mode, browser settings)
  }
  if (!raw) return null;
  try {
    const data = JSON.parse(raw) as Partial<SavedBoard>;
    if (data.version !== 1 || !Array.isArray(data.lines)) return null;
    const lines = data.lines.filter(
      (l): l is Line => typeof l?.id === "string" && typeof l?.latex === "string",
    );
    if (lines.length === 0) return null;
    return lines.slice(0, MAX_LINES);
  } catch {
    return null;
  }
}

export function saveBoard(storage: Pick<Storage, "setItem">, lines: Line[]): void {
  const data: SavedBoard = { version: 1, lines: lines.map(({ id, latex }) => ({ id, latex })) };
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // Storage full or blocked: the board still works, it just isn't saved.
  }
}

/** All lines as LaTeX, one per line, for "Copy as LaTeX". */
export function boardAsLatex(lines: Line[]): string {
  return lines
    .map((l) => l.latex.trim())
    .filter(Boolean)
    .join("\n");
}
