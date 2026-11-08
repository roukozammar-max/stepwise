# Stepwise roadmap

Each checkbox is sized for one Claude Code session and one GitHub issue.
Tick tasks as they're done. Current phase: **1**.

## Phase 0: Foundations (week 1)

- [x] Run the verifier locally (`verifier/README.md`) and see tests + eval pass
- [x] Have Claude walk you through `verifier.py`, then make one small change yourself
- [x] Push to GitHub and see CI go green
- [ ] Add 20+ eval cases from your own worksheets with `/add-eval-cases`
- [x] Fix or document anything the new cases break (every fix gets a test)

Done when: the eval has 66+ steps, CI is green, and you can explain what
happens inside `check_step` from start to finish.

## Phase 1: Single-player web app (weeks 2–3)

- [x] Write the spec: have Claude interview you, then save `docs/SPEC-phase1.md`
- [x] Scaffold `web/`: Next.js, TypeScript, Tailwind
- [x] Board page: an ordered list of lines you can add, edit and delete
- [x] Maths input with MathLive, display with KaTeX
- [x] Call `/verify` after typing pauses; show ✅/❌/❓, the message and the counterexample on each line
- [x] Allow the web app's origin in the API (CORS)
- [ ] Dockerfile for `verifier/`; deploy the API (Fly.io, Railway or Render)
- [ ] Deploy `web/` on Vercel with the API URL as an environment variable
- [ ] Root README: live link and a screenshot or GIF
- [ ] Drag to reorder lines
- [ ] Undo/redo across lines

Done when: you use it from the live URL for your own homework.

## Phase 2: Multiplayer (weeks 4–6)

- [ ] Spec: `docs/SPEC-phase2.md` (board data model, who triggers checks)
- [ ] `sync/`: Hocuspocus server; a board is a Y.Array of lines {id, latex, author, verdict}
- [ ] Connect `web/` to the sync server; presence and live cursors
- [ ] Sign-in with Supabase; boards table; invite link
- [ ] Save boards to Postgres
- [ ] Server-side checks: on change, wait ~500 ms, verify only changed steps, write the verdict into the board
- [ ] Load test: 5 people typing on one board

Done when: four classmates solve a worksheet together on one board.

## Phase 3: AI hints (weeks 7–8)

- [ ] Spec: `docs/SPEC-phase3.md` (prompt, guardrails, cost limits)
- [ ] `/hint` endpoint, called only on ❌ and only when asked; prompt uses the two lines and the counterexample
- [ ] Run `hint_reveals_answer` before showing a hint; regenerate or fall back to a generic nudge
- [ ] Cache hints per (previous line, line); rate-limit per user
- [ ] Log prompts and responses (Langfuse)
- [ ] Hint eval: 50 wrong steps, measure leak rate and score usefulness 1–5 yourself

Done when: the hint leak rate is measured and in the README.

## Phase 4: Proof and users (weeks 9–10)

- [ ] Comments on a single step (for teaching assistants)
- [ ] Replay: scrub through how a board's solution evolved
- [ ] Grow the eval to 500 steps (from real boards, with permission)
- [ ] 90-second demo video; README numbers updated
- [ ] Get users: class group chats, one TD instructor

Stretch: free-form tldraw canvas, handwriting photo → LaTeX, physics unit
checks, inequalities.
