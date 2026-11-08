# Stepwise web app

The board: type a derivation line by line, and each step is checked by the
verifier API as you go. Spec: [`docs/SPEC-phase1.md`](../docs/SPEC-phase1.md).

## Run it

From the repo root on Windows, double-click `start-stepwise.bat`. By hand:

```bash
npm ci          # install libraries (also copies MathLive's fonts into public/)
npm run dev     # http://localhost:3000, needs the API on http://127.0.0.1:8000
```

The API address comes from `NEXT_PUBLIC_API_URL` (see `.env.example`); it
defaults to `http://127.0.0.1:8000`. The API must allow this page's address
in `ALLOWED_ORIGINS` (it allows localhost:3000 by default).

Checks before committing:

```bash
npm run lint && npm run typecheck && npm test && npm run build
```

## How it fits together

```
app/page.tsx             server page, renders BoardLoader
components/
  BoardLoader.tsx        loads Board in the browser only (it needs localStorage)
  Board.tsx              the page: lines, editing, saving, banners
  BoardLine.tsx          one line: number, maths, delete button, status, message
  MathInput.tsx          MathLive field for the line being edited
  MathView.tsx           KaTeX rendering for the other lines
  StatusBadge.tsx        ✓ ✗ ? and the "checking" spinner
lib/
  board.ts               lines, editing actions (a reducer), saving to localStorage
  verify.ts              API calls, matching answers back to lines
  useChecker.ts          when to check: typing pause, Enter, newest answer wins
  *.test.ts              unit tests (Vitest)
scripts/copy-mathlive-assets.mjs   copies MathLive's fonts to public/mathlive/fonts
```

## Design decisions worth knowing

- **A verdict belongs to a pair of lines.** Whether line 3 is right depends on
  line 2 and line 3. Each verdict is stored with a key made of both lines and
  only shown while both are unchanged. So an edit instantly marks the two
  affected lines as "checking", and an old answer arriving late can never
  show the wrong verdict.
- **The whole board is sent each time.** The API caches each (previous line,
  line) pair, so unchanged steps cost nothing. Simpler than tracking diffs.
- **Only the newest answer counts.** Each request gets an increasing number;
  an older answer that arrives after a newer one is ignored.
- **Empty lines are skipped**, so a step compares a line with the previous
  non-empty line, exactly like the API.
- **MathLive for the line being edited, KaTeX for the rest**: one live editor
  instead of 50 keeps the page fast. MathLive reports changes slightly after
  each keystroke, so the field sends its final value when it closes (Enter,
  arrows, clicking away); otherwise fast typing could be lost.
- **MathLive's LaTeX works with the checker as is.** All 73 expressions from
  the eval set come out of MathLive unchanged, and typed brackets become
  `\left( \right)`, which the parser reads fine. No clean-up layer needed.
- **Saved in the browser** under `stepwise.board.v1`; verdicts aren't saved,
  the board is re-checked on load.

## Tested

- 13 unit tests (`npm test`) for the board actions, saving and answer matching.
- The spec's acceptance checks 1 to 10 were run in a real browser (Chromium,
  via Playwright), plus keyboard navigation and phone width: all passing.
  Check 11 (use it for real homework) is yours.
