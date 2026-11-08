"use client";

import { MathInput, type Caret } from "./MathInput";
import { MathView } from "./MathView";
import { StatusBadge, type LineState } from "./StatusBadge";

type Props = {
  number: number;
  latex: string;
  /** null: no status (empty line or starting point) */
  state: LineState | null;
  message: string;
  isStart: boolean;
  editing: { caret: Caret; session: number } | null;
  onActivate: () => void;
  onChange: (latex: string) => void;
  onEnter: () => void;
  onBackspaceWhenEmpty: () => void;
  onMoveOut: (direction: "previous" | "next", caret: Caret) => void;
  onBlur: () => void;
  onDelete: () => void;
};

export function BoardLine(props: Props) {
  const { number, latex, state, message, isStart, editing } = props;
  const showMessage = state === "incorrect" || state === "unknown" || state === "offline";

  return (
    <li className="group" data-testid="board-line" data-state={state ?? (isStart ? "start" : "empty")}>
      <div
        className={`flex items-center gap-3 rounded-lg px-2 py-1.5 transition-colors ${
          editing ? "bg-surface ring-1 ring-accent/40" : "hover:bg-surface"
        }`}
      >
        <span className="w-6 shrink-0 text-right text-sm tabular-nums text-muted select-none">
          {number}
        </span>

        <div className="min-w-0 flex-1 text-lg">
          {editing ? (
            <MathInput
              key={editing.session}
              initialValue={latex}
              caret={editing.caret}
              label={`Line ${number}`}
              onChange={props.onChange}
              onEnter={props.onEnter}
              onBackspaceWhenEmpty={props.onBackspaceWhenEmpty}
              onMoveOut={props.onMoveOut}
              onBlur={props.onBlur}
            />
          ) : (
            <button
              type="button"
              onClick={props.onActivate}
              aria-label={`Edit line ${number}`}
              className="block min-h-9 w-full cursor-text overflow-x-auto py-1 text-left"
            >
              {latex.trim() ? (
                <MathView latex={latex} />
              ) : (
                <span className="text-base text-muted">Click to type…</span>
              )}
            </button>
          )}
        </div>

        <button
          type="button"
          onClick={props.onDelete}
          aria-label={`Delete line ${number}`}
          title="Delete line"
          className="shrink-0 rounded px-1.5 text-muted opacity-0 transition-opacity hover:text-bad focus:opacity-100 group-hover:opacity-100"
        >
          ×
        </button>

        <span className="flex w-7 shrink-0 justify-center">
          {state && <StatusBadge state={state} />}
        </span>
      </div>

      {showMessage && message && (
        <p
          className={`ml-11 mr-10 mb-1 rounded-md px-3 py-1.5 text-sm ${
            state === "incorrect" ? "bg-bad-soft text-bad" : "bg-warn-soft text-warn"
          }`}
        >
          {message}
        </p>
      )}
    </li>
  );
}
