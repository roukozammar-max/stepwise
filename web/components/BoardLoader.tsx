"use client";

import dynamic from "next/dynamic";

// The board reads localStorage and uses MathLive, which only exist in the
// browser, so it is not rendered on the server.
const Board = dynamic(() => import("./Board"), {
  ssr: false,
  loading: () => <p className="px-4 py-12 text-center text-sm text-muted">Loading your board…</p>,
});

export function BoardLoader() {
  return <Board />;
}
