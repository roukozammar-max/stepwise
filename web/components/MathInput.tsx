"use client";

/**
 * The editable maths field for the line being edited (MathLive).
 * MathLive is a browser-only web component, so it is loaded on demand and
 * created by hand; React just gives it a place on the page.
 */
import { useEffect, useRef } from "react";
import type { MathfieldElement } from "mathlive";

export type Caret = "start" | "end";

type Props = {
  initialValue: string;
  caret: Caret;
  label: string;
  onChange: (latex: string) => void;
  onEnter: () => void;
  onBackspaceWhenEmpty: () => void;
  onMoveOut: (direction: "previous" | "next", caret: Caret) => void;
  onBlur: () => void;
};

let mathLive: Promise<typeof import("mathlive")> | null = null;

function loadMathLive() {
  mathLive ??= import("mathlive").then((mod) => {
    // Fonts are copied to public/mathlive/fonts by scripts/copy-mathlive-assets.mjs
    mod.MathfieldElement.fontsDirectory = "/mathlive/fonts";
    mod.MathfieldElement.soundsDirectory = null;
    return mod;
  });
  return mathLive;
}

export function MathInput(props: Props) {
  const host = useRef<HTMLDivElement>(null);
  const latest = useRef(props);

  useEffect(() => {
    latest.current = props;
  });

  useEffect(() => {
    let field: MathfieldElement | null = null;
    let flush: () => void = () => {};
    let cancelled = false;

    void loadMathLive().then(({ MathfieldElement }) => {
      if (cancelled || !host.current) return;
      const mf = new MathfieldElement();
      field = mf;
      mf.setAttribute("aria-label", latest.current.label);
      // Attach first: MathLive only accepts most settings once it is on the page.
      host.current.appendChild(mf);
      mf.value = latest.current.initialValue;

      // MathLive reports changes slightly after the keystroke. Before the
      // field closes (Enter, arrows, clicking away), send the final value so
      // fast typing is never lost.
      let reported = mf.value;
      flush = () => {
        if (mf.value !== reported) {
          reported = mf.value;
          latest.current.onChange(reported);
        }
      };

      mf.addEventListener("input", () => flush());
      mf.addEventListener(
        "keydown",
        (event) => {
          if (event.key === "Enter") {
            event.preventDefault();
            event.stopPropagation();
            flush();
            latest.current.onEnter();
          } else if (event.key === "Backspace" && mf.value.trim() === "") {
            event.preventDefault();
            event.stopPropagation();
            latest.current.onBackspaceWhenEmpty();
          }
        },
        { capture: true },
      );
      // Fired when an arrow key tries to leave the field (start/end or top/bottom).
      mf.addEventListener("move-out", (event) => {
        const direction = event.detail.direction;
        event.preventDefault();
        flush();
        if (direction === "upward" || direction === "backward") {
          latest.current.onMoveOut("previous", "end");
        } else {
          latest.current.onMoveOut("next", direction === "forward" ? "start" : "end");
        }
      });
      mf.addEventListener("focusout", () => {
        flush();
        latest.current.onBlur();
      });

      mf.focus();
      requestAnimationFrame(() => {
        if (!cancelled) mf.position = latest.current.caret === "start" ? 0 : mf.lastOffset;
      });
    });

    return () => {
      cancelled = true;
      flush();
      field?.remove();
    };
  }, []);

  return <div ref={host} className="math-input min-h-9 w-full" />;
}
