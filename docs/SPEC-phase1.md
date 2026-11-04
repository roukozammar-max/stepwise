# Phase 1 spec: single-player web app

Status: agreed 2026-11-04. Roadmap: `docs/ROADMAP.md`, Phase 1.

## Goal

A web page where I type a derivation line by line and each step is checked
by the verifier API as I go. Done when I use it from the live URL for my own
homework.

## Who it's for

Just me. Classmates may open the link, but nothing is designed for them yet:
no accounts, no sharing, no onboarding beyond the starter example.

Laptop first (keyboard and mouse). It must open and be readable on a phone,
but phone typing doesn't have to be good.

## What the user sees

One page, one board. No routing beyond `/`.

```
Stepwise                                [Copy as LaTeX] [Clear board]

 1   \frac{d}{dx}\sin(x^2)
 2   = \cos(x^2) \cdot 2x                                         ✅
 3   = \cos(x^2)                                                  ❌
     Not equal: at x = 1, the previous line gives 1.081
     but this line gives 0.5403.
 4   |                                                     (typing…)
     + add line
```

- Each line is a maths field. The line being edited is a MathLive field;
  the other lines are shown with KaTeX. Clicking a line makes it editable.
- Line 1 is the starting point and never gets a verdict.
- Each later line shows one status on the right:
  - ⏳ checking (request in flight or waiting for the typing pause)
  - ✅ correct: icon only, no text
  - ❌ incorrect: icon, plus the message and counterexample under the line
  - ❓ unknown: icon, plus the reason under the line
  - nothing, for an empty line
- Dark mode follows the system light/dark setting.

## Editing

Must have before the first deploy:

| Action | How |
|---|---|
| Add a line at the end | "+ add line" under the last line |
| New line below the current one | Enter |
| Insert a line in the middle | Enter on any line inserts directly below it |
| Edit a line | Click it, type |
| Delete a line | Delete button on hover, or Backspace on an empty line |
| Move between lines | Up/Down arrows at the start/end of a field |
| Clear the board | "Clear board" button, with a confirm dialog |
| Copy as LaTeX | Copies all lines, one per line, to the clipboard |

After the first deploy (separate Phase 1 tasks):

- Reorder lines by dragging.
- Undo/redo (Ctrl+Z / Ctrl+Shift+Z) across lines, including bringing back
  a deleted line.

## Checking

- A line is checked about **800 ms after typing stops** in it, and
  immediately on Enter or when the field loses focus.
- A verdict depends on two lines (previous and current), so a change to
  line N affects the verdicts of lines N and N+1. Moving, inserting or
  deleting a line affects the line after it too.
- Each check sends the **whole board** to `POST /verify`. The server caches
  per (previous line, line), so unchanged steps come back fast. This keeps
  the web app simple: no client-side diffing.
- Empty lines are not sent. `api.py` drops blank lines anyway, which would
  shift step indexes, so the web app filters them itself and maps each
  result back to its line by position.
- Only the newest response counts. Each request gets an increasing number;
  a response that arrives after a newer request was sent is ignored, so an
  old verdict never overwrites a newer one.
- Limits match the API: at most 50 lines, 500 characters per line. The UI
  stops "+ add line" at 50 and shows a note.

### API contract (already exists)

Request:

```json
{"lines": ["\\frac{d}{dx}\\sin(x^2)", "= \\cos(x^2)"]}
```

Response: `{"steps": [...]}`, one entry per line sent, each with `line`
(0-based index among the lines sent), `status` (`start` | `correct` |
`incorrect` | `unknown`), `method`, `message` and, for `incorrect`, a
`counterexample`. Source: `StepResult` in `verifier/verifier.py`.

### When the API is slow or down

- The API is on a free tier that sleeps when idle, so the first check after
  a break can take 30–60 s. If a request takes over 3 s, show a banner:
  "Waking up the checker, this can take up to a minute."
- If a request fails (network error or 5xx), show a banner "Can't reach the
  checker" with a Retry button, and mark affected lines ❓. Editing keeps
  working; nothing is lost.
- The client gives up on a request after 90 s.

## Saving

- The board is saved to browser `localStorage` under the key
  `stepwise.board.v1` on every change.
- Saved data: `{"version": 1, "lines": [{"id": "...", "latex": "..."}]}`.
  Each line has a stable random id so React can track it and so the Phase 2
  model (`{id, latex, author, verdict}`) is a small step away.
- Verdicts are not saved; the board is re-checked when the page loads.
- If saved data is missing or unreadable, start with the starter example.
- Known limit: the board lives in one browser. Clearing site data or
  switching device loses it. Phase 2 moves boards to Postgres.

## Starter example

On first visit (nothing saved), the board contains a short derivation that
shows all three outcomes, for example:

```
\frac{d}{dx}\sin(x^2)
= \cos(x^2) \cdot 2x
= \cos(x^2)
```

"Clear board" empties it. The example is only shown again if storage is
empty.

## Tech choices

| Part | Choice | Why |
|---|---|---|
| Web app | Next.js + TypeScript + Tailwind in `web/` | From the roadmap; Vercel deploys it with no config |
| Maths input | MathLive | Editable maths field that outputs LaTeX |
| Maths display | KaTeX | Fast static rendering for lines not being edited |
| State | React `useState`/`useReducer` in the board page | One page, one user: no state library needed |
| API host | Render free tier, Docker image from `verifier/Dockerfile` | $0; cold starts accepted |
| Web host | Vercel free tier | |
| Config | `NEXT_PUBLIC_API_URL` in `web/.env.local`, listed in `.env.example` | Secret-free, but keeps the URL out of code |
| CORS | API reads allowed origins from an `ALLOWED_ORIGINS` env var (comma-separated): `http://localhost:3000` and the Vercel URL | Only our own web app can call it from a browser |

New dependencies beyond the roadmap: none planned. Drag-to-reorder may need
a library (for example `@dnd-kit`); decide in that task and say why.

## Out of scope for Phase 1

- Accounts, sign-in, sharing, multiple boards, multiplayer (Phase 2)
- AI hints (Phase 3)
- Comments, replay (Phase 4)
- Good phone typing, handwriting input, free-form canvas
- Changes to how steps are judged. If MathLive output exposes verifier
  gaps, log them as issues; any verifier fix follows the usual rules
  (tests, eval, new eval cases).

## Risks

- **MathLive's LaTeX vs. the parser.** MathLive may emit LaTeX that
  `parse_latex` doesn't handle (`\left(`…`\right)`, `\cdot` variants,
  `\differentialD`, `\exponentialE`, implicit `\,` spacing). First task in
  the MathLive step: type every expression from `eval_cases.json` through
  MathLive and record which come out unparseable. Fix in the web app
  (MathLive output settings, or a small clean-up function before sending)
  where possible; otherwise file a verifier issue.
- **Cold starts** make the first check slow. Accepted for now; the banner
  explains it. Revisit with a ~$5/month always-on host if it gets annoying.
- **Flicker.** Verdicts changing while typing could be distracting. The
  800 ms pause plus "only the newest response counts" should prevent it;
  adjust the delay after real use.

## Acceptance checks

Phase 1 is done when all of these work on the live URL:

1. Typing the starter example gives ✅ on line 2 and ❌ with the
   counterexample on line 3.
2. `x^2 = 4` then `x = 2` gives ❌ "This step lost x = -2."
3. Editing line 2 updates the verdicts of lines 2 and 3 without a reload.
4. Inserting a line between two lines re-checks both affected steps.
5. Deleting a line, then reloading the page, shows the board without it.
6. With the API stopped, the "Can't reach the checker" banner appears,
   editing still works, and Retry recovers once the API is back.
7. After the API has slept, the first check shows the "Waking up" banner
   and then the verdict.
8. "Copy as LaTeX" pastes the lines into a text editor, one per line.
9. A 50-line board can't get a 51st line.
10. The page is readable in both light and dark system themes.
11. I've used it for at least one real homework problem.

## Task order

Matches `docs/ROADMAP.md` Phase 1:

1. Scaffold `web/` (Next.js, TypeScript, Tailwind).
2. Board page: lines with add, edit, delete, Enter, insert-in-middle,
   localStorage, starter example, clear, copy as LaTeX. Plain text inputs
   are fine at this step.
3. MathLive input and KaTeX display, including the LaTeX-compatibility
   check from Risks.
4. Call `/verify` after typing pauses; show statuses, messages,
   counterexamples, the slow/down banners.
5. CORS with `ALLOWED_ORIGINS` in the API (verifier change: tests and eval
   must pass).
6. `verifier/Dockerfile`; deploy the API on Render.
7. Deploy `web/` on Vercel with `NEXT_PUBLIC_API_URL`.
8. Root README: live link and a screenshot or GIF.
9. Drag to reorder lines.
10. Undo/redo.
