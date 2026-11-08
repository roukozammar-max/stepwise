"use client";

/**
 * The board page: the list of lines, editing, saving and checking.
 * Rendered in the browser only (see BoardLoader), because it reads the saved
 * board from localStorage when it starts.
 */
import { useEffect, useMemo, useReducer, useState } from "react";
import {
  MAX_LINES,
  boardAsLatex,
  boardReducer,
  loadBoard,
  newId,
  saveBoard,
  starterBoard,
  type Line,
} from "@/lib/board";
import { useChecker } from "@/lib/useChecker";
import { checkableLines } from "@/lib/verify";
import { BoardLine } from "./BoardLine";
import type { Caret } from "./MathInput";
import type { LineState } from "./StatusBadge";

type Editing = { id: string; caret: Caret; session: number } | null;

function initialLines(): Line[] {
  return loadBoard(window.localStorage) ?? starterBoard();
}

export default function Board() {
  const [lines, dispatch] = useReducer(boardReducer, undefined, initialLines);
  const [editing, setEditing] = useState<Editing>(null);
  const [copied, setCopied] = useState(false);
  const { verdicts, status, errorMessage, checkNow } = useChecker(lines);

  useEffect(() => {
    saveBoard(window.localStorage, lines);
  }, [lines]);

  const steps = useMemo(() => new Map(checkableLines(lines).map((s) => [s.id, s])), [lines]);
  const full = lines.length >= MAX_LINES;

  function edit(id: string, caret: Caret = "end") {
    setEditing((current) => ({ id, caret, session: (current?.session ?? 0) + 1 }));
  }

  function lineStatus(line: Line): { state: LineState | null; message: string; isStart: boolean } {
    const step = steps.get(line.id);
    if (!step) return { state: null, message: "", isStart: false };
    if (step.isStart) return { state: null, message: "", isStart: true };
    const verdict = verdicts[line.id];
    if (verdict && verdict.key === step.key) {
      return { state: verdict.status, message: verdict.message, isStart: false };
    }
    if (status === "error") {
      return {
        state: "offline",
        message: "Not checked yet: the checker can't be reached.",
        isStart: false,
      };
    }
    return { state: "checking", message: "", isStart: false };
  }

  function insertAfter(id: string) {
    if (full) return;
    const id2 = newId();
    dispatch({ type: "insertAfter", id, newId: id2 });
    edit(id2);
    checkNow();
  }

  function remove(id: string, focusNeighbour: boolean) {
    const i = lines.findIndex((l) => l.id === id);
    const neighbour = lines[i - 1] ?? lines[i + 1];
    dispatch({ type: "delete", id });
    if (focusNeighbour && neighbour) edit(neighbour.id);
    else setEditing((current) => (current?.id === id ? null : current));
  }

  function moveOut(id: string, direction: "previous" | "next", caret: Caret) {
    const i = lines.findIndex((l) => l.id === id);
    const target = lines[direction === "previous" ? i - 1 : i + 1];
    if (target) edit(target.id, caret);
  }

  function addLine() {
    if (full) return;
    const id = newId();
    dispatch({ type: "append", newId: id });
    edit(id);
  }

  function clearBoard() {
    if (!window.confirm("Clear the whole board? This can't be undone.")) return;
    const id = newId();
    dispatch({ type: "clear", newId: id });
    edit(id);
  }

  async function copyAsLatex() {
    try {
      await navigator.clipboard.writeText(boardAsLatex(lines));
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      window.alert("Your browser blocked copying. Select the lines and copy them by hand.");
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:py-12">
      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Stepwise</h1>
          <p className="text-sm text-muted">Write a derivation line by line. Every step is checked.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={copyAsLatex} className="btn">
            {copied ? "Copied" : "Copy as LaTeX"}
          </button>
          <button type="button" onClick={clearBoard} className="btn">
            Clear board
          </button>
        </div>
      </header>

      {status === "slow" && (
        <div role="status" className="mb-4 rounded-lg bg-info-soft px-4 py-3 text-sm text-info">
          Still checking… The checker sleeps when nobody is using it, so the first check after a
          break can take up to a minute.
        </div>
      )}
      {status === "error" && (
        <div
          role="alert"
          className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg bg-bad-soft px-4 py-3 text-sm text-bad"
        >
          <span>
            Can&apos;t reach the checker. {errorMessage} Your board is saved; you can keep
            editing.
          </span>
          <button type="button" onClick={checkNow} className="btn">
            Retry
          </button>
        </div>
      )}

      <ol className="space-y-0.5" aria-label="Derivation">
        {lines.map((line, i) => {
          const { state, message, isStart } = lineStatus(line);
          const isEditing = editing?.id === line.id;
          return (
            <BoardLine
              key={line.id}
              number={i + 1}
              latex={line.latex}
              state={state}
              message={message}
              isStart={isStart}
              editing={isEditing ? { caret: editing.caret, session: editing.session } : null}
              onActivate={() => edit(line.id)}
              onChange={(latex) => dispatch({ type: "update", id: line.id, latex })}
              onEnter={() => insertAfter(line.id)}
              onBackspaceWhenEmpty={() => {
                if (lines.length > 1) remove(line.id, true);
              }}
              onMoveOut={(direction, caret) => moveOut(line.id, direction, caret)}
              onBlur={() => {
                checkNow();
                setEditing((current) => (current?.id === line.id ? null : current));
              }}
              onDelete={() => remove(line.id, false)}
            />
          );
        })}
      </ol>

      <div className="mt-2 pl-11">
        {full ? (
          <p className="text-sm text-muted">A board can have at most {MAX_LINES} lines.</p>
        ) : (
          <button type="button" onClick={addLine} className="text-sm text-muted hover:text-fg">
            + add line
          </button>
        )}
      </div>

      <footer className="mt-12 border-t border-line pt-4 text-xs leading-relaxed text-muted">
        <p>
          <kbd>Enter</kbd> new line · <kbd>↑</kbd> <kbd>↓</kbd> move between lines ·{" "}
          <kbd>Backspace</kbd> on an empty line deletes it · Type <code>/</code> for a fraction,{" "}
          <code>^</code> for a power, <code>sqrt</code> for a square root.
        </p>
        <p className="mt-1">
          Your board is saved in this browser only. Checks are done by SymPy, a computer algebra
          system: ✓ means the step is mathematically equal to the line above.
        </p>
      </footer>
    </div>
  );
}
