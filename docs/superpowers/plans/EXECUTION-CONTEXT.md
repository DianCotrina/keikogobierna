# Execution Context for Delegated Plans

Read this BEFORE executing any plan in this directory. It encodes the conventions, environment facts, and quality bar established during the project's foundation phases so a fresh session (any model) executes at the same standard without re-deriving them. When a plan and this file conflict, the plan wins; when the user and anything conflict, the user wins.

## Project in one paragraph

`keikogobierna` tracks the fulfillment of Peru's "Perú con Orden" 2026–2031 government plan (Keiko Fujimori / Fuerza Popular). Static Astro 7 site (Tailwind v4 via `@tailwindcss/vite`), 24 pages: landing + 23 topic pages at `/temas/{slug}/`. All content is derived at build time from a versioned data tree extracted from the official PDF. This is a public accountability dataset — data integrity beats convenience everywhere.

## Non-negotiable conventions

- **Language policy:** code identifiers, JSON keys, file/folder names, enum values, comments, commits → English. Everything a visitor reads (page copy, titles, meta descriptions, labels, URL paths/slugs/anchors like `/temas/...`, `#tablero`) → Spanish (Peru). If unsure whether a string is user-facing, it is.
- **Status vocabulary:** `fulfilled | in_progress | no_progress | unfulfilled`. Spanish labels (Cumplida / En progreso / Sin avance / Incumplida) exist ONLY in `src/lib/statuses.mjs`. Colors: verde / ambar / plomo / rojo.
- **Stable IDs:** topics `t{pillar}-{n}`; proposals `{topic}.P{nn}`; first-100-days `{topic}.C{nn}`; goals `{topic}.M{nn}`. IDs referenced by `src/data/tracking.json` may NEVER change. (Exception, defined in the curation plan: proposal renumbering is allowed only while no proposal id appears in tracking.)
- **Two-layer tracking rule:** progress percentages count ONLY goals (metas al 2031). Proposals are listed and individually trackable but never enter a %.
- **Honest data:** never fabricate progress, dates, or events. Empty states say so in Spanish. Source-document typos are preserved verbatim in extracted text.
- **Data tree is guarded:** after ANY edit under `src/data/`, run `npm run validate` (wraps `tools/validate_plan_data.py`). `src/data/plan/topics/*` is generated — change the extractor (`tools/extract_plan_pdf.py`), never hand-edit. `src/data/plan/goals/goals-2031.json` is hand-curated. `src/data/tracking.json` is the living layer.
- **Design system ("tinta"):** black ink `#141417` on paper `#F5F3EE`, Peru-red `#C8102E` accents only; Archivo Black / Source Serif 4 / IBM Plex Mono; paper grain, pen-stroke SVGs, rubber-stamp chips; transform/opacity-only animations with spring easing; hover + focus-visible + active on every interactive element; `prefers-reduced-motion` respected. Tokens live in the `@theme` block of `src/styles/global.css`. Never introduce default-Tailwind-palette colors. The `frontend-design` skill must be invoked before writing frontend code when running under Claude Code (per CLAUDE.md).
- **Commits:** conventional-commit style subjects (feat/fix/refactor/docs/chore/data). End every commit with your harness's Co-Authored-By trailer. Stage only the files your task touches — never `git add -A`. Never amend reviewed commits; fixes are new commits.
- **Git identity:** commits must use the author email `33852507+DianCotrina@users.noreply.github.com` (GitHub blocks pushes exposing the private email). It's set in this clone's `git config user.email` — verify on a fresh clone.

## Environment facts (Mac, this machine)

- Node ≥ 26, npm. Scripts: `npm run dev` (Astro, port 3000), `build`, `preview` (also 3000), `test` (`node --test "tests/**/*.test.mjs"`), `validate`.
- **Port 3000: one instance ever.** Before starting a server: `lsof -ti :3000 | xargs kill`. Kill your servers when done.
- **Headless browser is Brave** (no Chrome): `"/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" --headless --disable-gpu --hide-scrollbars --window-size=W,H --virtual-time-budget=9000 --screenshot=out.png URL`. **Headless windows clamp to 500px minimum width** — a 390px screenshot silently renders at 500 and crops, which looks exactly like a page overflow bug but is not. For mobile widths, screenshot a local `frame.html` containing `<iframe src="…" style="width:390px;height:H;border:0">` at a ≥500px window and crop. `sips -c` crops from center, not top-left.
- Python 3 with stdlib only for `tools/*.py`. `pdftotext` at `/opt/homebrew/bin/` (poppler). `gh` CLI authenticated.
- Never screenshot `file:///` for the site — always serve first.
- Known bundler gotcha: `fs.readFileSync(new URL(...))` inside `src/lib/*.mjs` breaks under Astro/Vite (module relocation → ENOENT). Use static JSON imports `with { type: 'json' }` (works in Node 26 tests AND the build). This already bit us once.

## Execution protocol (subagent-driven development)

Execute plans with the superpowers subagent-driven-development skill. Its helper scripts live at `~/.claude/plugins/cache/claude-plugins-official/superpowers/<version>/skills/subagent-driven-development/scripts/` (`task-brief PLAN_FILE N`, `review-package BASE HEAD`).

- Work on a feature branch off `main`; commit the plan-execution ledger discipline: append one line per completed task to `.superpowers/sdd/progress.md` (gitignored) — it is the recovery map after context loss; trust it plus `git log` over memory.
- Fresh implementer subagent per task; hand it the task brief file + the plan's shared-contract sections + this file's relevant facts (paths, port, browser). Record the base SHA before dispatch.
- Independent reviewer subagent after every task with the diff package file; never tell a reviewer what not to flag. Fix Critical/Important findings via a fix dispatch + re-review; log Minor findings for the final review to triage.
- Model selection: cheapest tier when the plan contains the complete code (transcription); mid tier for prose-spec implementation and reviews; most capable available for the final whole-branch review.
- Final whole-branch review before PR; it triages the logged Minor list. Then push and open a PR (never merge your own PR without the user's explicit instruction; pushing may require the noreply email above).
- Verification bar: evidence before claims — run the commands, paste output in reports; every UI change gets screenshots that someone actually VIEWS (at least 2 look-fix rounds when round 1 shows issues); builds/tests/validator green before any commit claiming completion.

## Current deferred-items registry (source of truth for "known issues")

1. `t3-7.P17` stub proposal + `t2-6.P15` glued "Aeroportuaria" header — source-PDF artifacts (curation plan fixes these).
2. Validator doesn't enforce goals `indicator`/`table_topic` non-emptiness (curation plan).
3. `og:image`/`og:url` absent; alertas form has no backend; footer "Fuentes"/"Contacto" are `href="#"` (deploy plan fixes all).
4. `goalStats` zero-goal branch and multi-entry `updatesLog` sorting untested (tracking plan adds fixture tests).
5. Goal `t2-6.M02` preserves the document's own typo "4 metros de Lima" — intentional, do not "fix".

## Plan sequencing

All plans branch off `main` AFTER PR #3 (astro-migration) is merged. Recommended order: **B (curation) → A (deploy) → C (tracking)** — B changes proposal counts/IDs which A's built pages and C's tooling then consume; but A and C are independent of each other. Never run two plans' branches concurrently.
