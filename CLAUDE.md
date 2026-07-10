# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`keikogobierna` is a website to track and follow the current government plan of Keiko (Peruvian politics). See [README.md](README.md).

## Commands

- `npm install` — install dependencies
- `npm run dev` — Astro dev server at http://localhost:3000
- `npm run build` — static build to `dist/`
- `npm run preview` — serve the `dist/` build locally
- `npm test` — run the data-layer test suite (`node --test tests/**/*.test.mjs`)
- `npm run validate` — validate `src/data/plan/` + `tracking.json` (`python3 tools/validate_plan_data.py`)
- Single test: `node --test tests/plan.test.mjs`

## Git Workflow

- **One branch per feature.** Start each feature on a fresh branch off the latest `main`. Don't continue new features on a branch whose PR already merged.
- **Branch names are typed**: `<type>/<short-kebab-name>`, where type is any valid conventional-commit type — most commonly `feat/`, `fix/`, `docs/`, `refactor/`, `chore/`, `test/`, `ci/` (e.g. `feat/index-rail`, `fix/rail-footer-overlap`, `refactor/donate-module`, `ci/deploy-workflow`). Match the type to the dominant commit type of the work; only `feat` and `fix` (or a `!` breaking change) move the version.
- **Merges are always rebase-and-merge.** Never create merge commits: locally, rebase the branch onto main and fast-forward; on GitHub PRs, use the "Rebase and merge" button — not "Create a merge commit" or "Squash and merge".
- **Keep active branches up to date.** While a feature branch is in flight, regularly run `git pull --rebase origin main` on it — at minimum before pushing and before opening or updating a PR. Resolve conflicts during the rebase; never back-merge main into the branch.
- After rebasing an already-pushed branch, push with `--force-with-lease` (never plain `--force`).
- **`main` is protected by the `protect-main` ruleset** (GitHub Settings → Rules): PRs required, the `checks` CI job must pass, linear history required, force pushes and deletion blocked. Direct pushes to `main` will be rejected. Repository admins can bypass — needed to merge release-please's release PRs, which never trigger CI (they're created by the Actions token); use bypass only for those.
- **Releases:** release-please maintains a release PR from conventional commits; merging it tags `vX.Y.Z`, publishes a GitHub Release, and updates `CHANGELOG.md`. `feat:` → minor, `fix:` → patch, `feat!:`/`BREAKING CHANGE:` → major — write commit messages accordingly.

## Language Policy

- **Development conversation is in English**: chat with the user, code comments, commit messages, workflow docs, and variable/function names.
- **Everything user-facing is in Spanish (Peru)**: page `<title>`, meta tags, headings, buttons, labels, body copy, form placeholders, error messages, alt text — anything a visitor of the site reads.
- Never mix languages in the UI. If unsure whether a string is user-facing, it probably is — write it in Spanish.

## Always Do First

- **Invoke the `frontend-design` skill** before writing any frontend code, every session, no exceptions.

---

## The WAT Architecture

This project follows the Workflows → Agents → Tools architecture.

**Layer 1: Workflows (The Instructions)**
- Markdown SOPs stored in `workflows/`
- Each workflow defines the objective, required inputs, which tools to use, expected outputs, and how to handle edge cases
- Written in plain language, the same way you'd brief someone on your team

**Layer 2: Agents (The Decision-Maker)**
- This is your role. You're responsible for intelligent coordination.
- Read the relevant workflow, run tools in the correct sequence, handle failures gracefully, and ask clarifying questions when needed
- You connect intent to execution without trying to do everything yourself
- Example: If you need to pull data from a website, don't attempt it directly. Read `workflows/scrape_website.md`, figure out the required inputs, then execute `tools/scrape_single_site.py`

**Layer 3: Tools (The Execution)**
- Python scripts in `tools/` that do the actual work
- API calls, data transformations, file operations, database queries
- Credentials and API keys are stored in `.env`
- These scripts are consistent, testable, and fast

**Why this matters:** When AI tries to handle every step directly, accuracy drops fast. If each step is 90% accurate, you're down to 59% success after just five steps. By offloading execution to deterministic scripts, you stay focused on orchestration and decision-making where you excel.

## How to Operate

**1. Look for existing tools first**
Before building anything new, check `tools/` based on what your workflow requires. Only create new scripts when nothing exists for that task.

**2. Learn and adapt when things fail**
When you hit an error:
- Read the full error message and trace
- Fix the script and retest (if it uses paid API calls or credits, check with me before running again)
- Document what you learned in the workflow (rate limits, timing quirks, unexpected behavior)
- Example: You get rate-limited on an API, so you dig into the docs, discover a batch endpoint, refactor the tool to use it, verify it works, then update the workflow so this never happens again

**3. Keep workflows current**
Workflows should evolve as you learn. When you find better methods, discover constraints, or encounter recurring issues, update the workflow. That said, don't create or overwrite workflows without asking unless explicitly told to. These are your instructions and need to be preserved and refined, not tossed after one use.

## The Self-Improvement Loop

Every failure is a chance to make the system stronger:
1. Identify what broke
2. Fix the tool
3. Verify the fix works
4. Update the workflow with the new approach
5. Move on with a more robust system

This loop is how the framework improves over time.

## Bottom Line

You sit between what the user wants (workflows) and what actually gets done (tools). Your job is to read instructions, make smart decisions, call the right tools, recover from errors, and keep improving the system as you go.

Stay pragmatic. Stay reliable. Keep learning.

---

# Frontend Web Design

## Hard Rules

- **Invoke the `frontend-design` skill** before writing any frontend code, every session, no exceptions.
- Never ship generic, templated-looking UI. Every design decision must be intentional (see Anti-Generic Guardrails).
- Verify visually: screenshot the result served from localhost, never claim a design works without looking at it.

## Anti-Generic Guardrails

- **Colors:** Never use default Tailwind palette (indigo-500, blue-600, etc.). Pick a custom brand color and derive from it.
- **Shadows:** Never use flat `shadow-md`. Use layered, color-tinted shadows with low opacity.
- **Typography:** Never use the same font for headings and body. Pair a display/serif with a clean sans. Apply tight tracking (`-0.03em`) on large headings, generous line-height (`1.7`) on body.
- **Gradients:** Layer multiple radial gradients. Add grain/texture via SVG noise filter for depth.
- **Animations:** Only animate `transform` and `opacity`. Never `transition-all`. Use spring-style easing.
- **Interactive states:** Every clickable element needs hover, focus-visible, and active states. No exceptions.
- **Images:** Add a gradient overlay (`bg-gradient-to-t from-black/60`) and a color treatment layer with `mix-blend-multiply`.
- **Spacing:** Use intentional, consistent spacing tokens — not random Tailwind steps.
- **Depth:** Surfaces should have a layering system (base → elevated → floating), not all sit at the same z-plane.

## Assets

- Always check the `assets/` folder before designing. It may contain logos, color guides, style guides, or images.
- If assets exist there, use them. Do not use placeholders where real assets are available.
- If a logo is present, use it. If a color palette is defined, use those exact values — do not invent brand colors.

## Output Defaults

- Pages and components follow the Astro architecture in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): `.astro` layouts in `src/layouts/`, `.astro` components in `src/components/`, `.astro` pages in `src/pages/`. One-off mockups/sketches may still be single files.
- **Data edits:**
  - `src/data/tracking.json`: Living state. Edit freely (log progress with date/status/evidence), then run `python3 tools/validate_plan_data.py`.
  - `src/data/plan/` (topics, index, goals): Curated or auto-extracted from PDF. Do not hand-edit proposals or first-100-days actions in `topics/*.json` — regenerate via `tools/extract_plan_pdf.py` if the PDF changes. Goals (`src/data/plan/goals/goals-2031.json`) are hand-curated; run the validator after any goal edit.
- Tailwind CSS v4 via `@tailwindcss/vite`; design tokens live in the `@theme` block of [src/styles/global.css](src/styles/global.css)
- Placeholder images: `https://placehold.co/WIDTHxHEIGHT`
- Mobile-first responsive

## Reference Images

- If a reference image is provided: match layout, spacing, typography, and color exactly. Swap in placeholder content (images via `https://placehold.co/`, generic copy). Do not improve or add to the design.
- If no reference image: design from scratch with high craft (see Anti-Generic Guardrails above).
- Screenshot your output, compare against reference, fix mismatches, re-screenshot. Do at least 2 comparison rounds. Stop only when no visible differences remain or user says so.

## Local Server

- **Always serve on localhost** — never screenshot a `file:///` URL.
- Start the dev server: `npm run dev` (Astro dev server at `http://localhost:3000`)
- Start it in the background before taking any screenshots.
- If the server is already running, do not start a second instance.
