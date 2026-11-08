"use client";

/** Static maths for lines that aren't being edited (KaTeX: fast, no editor). */
import { useMemo } from "react";
import katex from "katex";

export function MathView({ latex }: { latex: string }) {
  // throwOnError: false shows unreadable LaTeX in red instead of crashing.
  // KaTeX escapes everything and ignores \href etc. by default (trust: false).
  const html = useMemo(
    () => katex.renderToString(latex, { throwOnError: false, displayMode: false }),
    [latex],
  );
  return <span className="math-view" dangerouslySetInnerHTML={{ __html: html }} />;
}
