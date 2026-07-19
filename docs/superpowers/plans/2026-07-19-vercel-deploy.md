# Vercel Production Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the static site to Vercel production, deployed from GitHub Actions on every merge to `main`, in time for the July 28 launch.

**Architecture:** A single GitHub Actions workflow drives the Vercel CLI (`vercel pull` → `vercel build --prod` → `vercel deploy --prebuilt --prod`). Vercel's own Git integration stays disabled, so Vercel never watches the repo and never tries to build the orphan data branches. The site remains fully static (`output: 'static'`) — no adapter, no SSR — and the Ultimitas runtime fetch from `raw.githubusercontent.com` is host-independent, so the data pipeline is untouched.

**Tech Stack:** Astro 7 (static), GitHub Actions, Vercel CLI, Node 22.

**Spec:** `docs/superpowers/specs/2026-07-19-vercel-deploy-design.md`

## Global Constraints

- `output: 'static'` stays; **no `@astrojs/vercel` adapter**, no SSR, no new npm dependency.
- Vercel's Git integration is **disabled** — the workflow is the only thing that deploys.
- **Production only.** No PR preview deploys in this plan.
- Deploys trigger on push to `main` and on `workflow_dispatch` — never from a data branch.
- The scrapers, `tools/`, `src/data/`, and the data-branch pattern are **not modified by this plan**.
- Node 22 in workflows (matches `.github/workflows/ci.yml`).
- Branch: `ci/vercel-deploy` (already created, already holds the spec commit). Conventional commits; rebase-and-merge only.
- Dev-facing text (workflow docs, comments, commit messages) in **English**; the site's user-facing copy is Spanish and is not touched here.
- The three repo secrets (`VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`) and all Vercel-dashboard/DNS actions are **performed by Diego**, not by the implementer.

## File Structure

| File | Responsibility |
|---|---|
| `vercel.json` (create) | Vercel platform config — CORS + cache headers on the `/api/*` open-data endpoints |
| `astro.config.mjs` (modify) | Add `site:` so absolute canonical/OG URLs and any future sitemap resolve |
| `.github/workflows/deploy.yml` (create) | The production deploy pipeline |
| `workflows/deploy.md` (create) | WAT SOP: one-time setup, operations, rollback, failure modes |
| `docs/ARCHITECTURE.md` (modify) | Replace the two now-false deployment statements |
| `README.md` (modify, Task 7 only) | Live URL, once the domain is serving |

---

### Task 1: `vercel.json` — headers for the open-data endpoints

The site's two datos-abiertos endpoints already declare an open license, so they must be fetchable cross-origin from a browser. Vercel serves static files with no CORS header by default.

**Files:**
- Create: `vercel.json`

**Interfaces:**
- Consumes: nothing.
- Produces: an `/api/(.*)` header rule that Task 6 verifies live with `curl`.

- [ ] **Step 1: Create `vercel.json`**

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "headers": [
    {
      "source": "/api/(.*)",
      "headers": [
        { "key": "Access-Control-Allow-Origin", "value": "*" },
        { "key": "Cache-Control", "value": "public, max-age=0, s-maxage=3600" }
      ]
    }
  ]
}
```

- [ ] **Step 2: Verify the file is valid JSON with the expected shape**

Run:
```bash
python3 -c "
import json
c = json.load(open('vercel.json'))
rule = c['headers'][0]
assert rule['source'] == '/api/(.*)', rule['source']
keys = {h['key'] for h in rule['headers']}
assert 'Access-Control-Allow-Origin' in keys, keys
assert 'Cache-Control' in keys, keys
print('vercel.json OK')
"
```
Expected: `vercel.json OK`

- [ ] **Step 3: Verify the build is unaffected and still emits the endpoints**

Run:
```bash
npm run build && ls dist/api/
```
Expected: build completes with `28 page(s) built`, and `ls` lists `plan.json` and `tracking.json`.

Note: the headers themselves cannot be tested locally — they are applied by Vercel's edge at serve time. Task 6 verifies them against the live deployment.

- [ ] **Step 4: Commit**

```bash
git add vercel.json
git commit -m "ci: serve the open-data endpoints with CORS and cache headers

/api/plan.json and /api/tracking.json declare an open-data license, so
they need Access-Control-Allow-Origin to be usable from a browser on
another origin. s-maxage caches them at the edge for an hour; they only
change on deploy, which invalidates the cache anyway.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `astro.config.mjs` — set the production `site`

`site` feeds absolute URL generation (canonical links, `og:url`, any future sitemap). It has no visible effect on today's output — nothing currently emits an absolute URL — so this is forward-looking config that prevents a wrong-URL gotcha later. The initial value is the `vercel.app` URL; Task 7 flips it to the custom domain.

**Files:**
- Modify: `astro.config.mjs`

**Interfaces:**
- Consumes: nothing.
- Produces: `site: 'https://keikogobierna.vercel.app'`, which Task 7 replaces with the custom domain.

- [ ] **Step 1: Add the `site` field**

Replace the whole file with:

```js
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  // Production origin. Feeds absolute canonical/OG URLs and any future sitemap.
  // Update this if the production domain changes.
  site: 'https://keikogobierna.vercel.app',
  output: 'static',
  server: { port: 3000 },
  vite: { plugins: [tailwindcss()] },
});
```

- [ ] **Step 2: Verify the config parses and `site` is set**

Run:
```bash
node -e "
import('./astro.config.mjs').then((m) => {
  const s = m.default.site;
  if (s !== 'https://keikogobierna.vercel.app') throw new Error('site not set, got: ' + s);
  if (m.default.output !== 'static') throw new Error('output must stay static, got: ' + m.default.output);
  console.log('site =', s, '| output =', m.default.output);
});
"
```
Expected: `site = https://keikogobierna.vercel.app | output = static`

- [ ] **Step 3: Verify the build still succeeds**

Run: `npm run build`
Expected: `28 page(s) built`, no warnings about `site`.

- [ ] **Step 4: Commit**

```bash
git add astro.config.mjs
git commit -m "ci: set the production site origin

Absolute canonical/OG URLs and any future sitemap need a site origin.
Points at the vercel.app URL until the custom domain's DNS is live.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: `.github/workflows/deploy.yml` — the deploy pipeline

**Files:**
- Create: `.github/workflows/deploy.yml`

**Interfaces:**
- Consumes: repo secrets `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (added by Diego in Task 6).
- Produces: a workflow named `deploy` with a `production` job, dispatchable via `gh workflow run deploy.yml`.

- [ ] **Step 1: Create the workflow**

```yaml
name: deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

# One production deploy at a time — a newer main supersedes an in-flight older one.
concurrency:
  group: deploy-production
  cancel-in-progress: true

# Only needs to read the repo; it calls Vercel, not the GitHub API.
permissions:
  contents: read

env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}
  VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}

jobs:
  production:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
          cache: npm
      - name: Install the Vercel CLI
        run: npm install --global vercel@latest
      - name: Pull project settings from Vercel
        run: vercel pull --yes --environment=production --token="$VERCEL_TOKEN"
      - name: Build (runs npm run build -> astro build)
        run: vercel build --prod --token="$VERCEL_TOKEN"
      - name: Deploy the prebuilt output to production
        run: vercel deploy --prebuilt --prod --token="$VERCEL_TOKEN"
```

- [ ] **Step 2: Verify the workflow YAML parses and has the expected shape**

Run:
```bash
python3 -c "
import yaml
w = yaml.safe_load(open('.github/workflows/deploy.yml'))
# PyYAML (YAML 1.1) parses a bare \`on:\` key as boolean True, so accept either.
on = w.get('on', w.get(True))
assert on['push']['branches'] == ['main'], on
assert 'workflow_dispatch' in on, on
assert w['concurrency']['cancel-in-progress'] is True, w['concurrency']
assert w['permissions'] == {'contents': 'read'}, w['permissions']
runs = [s.get('run', '') for s in w['jobs']['production']['steps']]
for needle in ('vercel pull', 'vercel build --prod', 'vercel deploy --prebuilt --prod'):
    assert any(needle in r for r in runs), (needle, runs)
print('deploy.yml OK -', len(runs), 'steps')
"
```
Expected: `deploy.yml OK - 6 steps`

- [ ] **Step 3: Verify GitHub accepts the workflow file**

This only works after the branch is pushed (Task 5). For now confirm no other workflow was disturbed:

Run: `ls .github/workflows/`
Expected: `ci.yml  deploy.yml  elperuano-scraper.yml  evidence-watcher.yml  release-please.yml  ultimitas-scraper.yml`

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/deploy.yml
git commit -m "ci: deploy production to Vercel on merge to main

Drives the Vercel CLI from Actions so all CI/CD stays on GitHub. Vercel's
own Git integration is disabled, so nothing deploys except this workflow
and the orphan data branches are never built. A failed build fails the
job and leaves the previous production deployment live.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: Documentation — deploy SOP, and correct the two false claims in ARCHITECTURE

`docs/ARCHITECTURE.md` currently states deployment is not wired, and recommends a `git.deploymentEnabled: false` toggle that this design makes unnecessary. Both are now wrong and must change in the same PR that makes them wrong.

**Files:**
- Create: `workflows/deploy.md`
- Modify: `docs/ARCHITECTURE.md`

**Interfaces:**
- Consumes: the workflow from Task 3 (documents its behavior).
- Produces: nothing other tasks depend on.

- [ ] **Step 1: Create the SOP at `workflows/deploy.md`**

```markdown
# Workflow: Production deploy (Vercel)

## Objective

Publish the built site to Vercel production. Unlike every other pipeline here — which
either files review issues or publishes to a data branch — this one serves the public
site itself. It deploys `main` only: never a data branch, never a PR.

## How it works

1. `.github/workflows/deploy.yml` runs on every push to `main`, and on manual dispatch.
2. It installs the Vercel CLI and runs three commands:
   - `vercel pull` — fetch the project's production settings
   - `vercel build --prod` — runs the project build (`npm run build` → `astro build`)
     and packages `dist/` into `.vercel/output`
   - `vercel deploy --prebuilt --prod` — uploads that output as a production deployment
3. Auth comes from three repo secrets: `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.

**Vercel's own Git integration is disabled.** Vercel does not watch the repo, so it never
tries to build the orphan data branches (`ultimitas-data`, `normas-archive`), which have
no `package.json` and would fail. This workflow is the only thing that ever deploys.

## What triggers a deploy — and what doesn't

- Merging any PR to `main` → production deploy. A `tracking.json` certification PR
  therefore republishes the site with the new status, which is the intent.
- Scraper runs → **no deploy**. They push to data branches, never to `main`. The
  Ultimitas page picks up new headlines at runtime by fetching `today.json` from
  `raw.githubusercontent.com`, which needs no rebuild.

## One-time setup (Vercel dashboard / registrar)

1. Register the domain.
2. `vercel link` (or the dashboard) to create the project → note `ORG_ID` and `PROJECT_ID`.
3. Project → Settings → Git → **disconnect / disable** the Git integration.
4. Account → Settings → Tokens → create a token for `VERCEL_TOKEN`.
5. GitHub → Settings → Secrets → Actions → add `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
6. Project → Settings → Domains → add the domain, then set the DNS records Vercel shows
   at the registrar.

## Operations

- **Manual redeploy:** `gh workflow run deploy.yml`, or Actions → deploy → Run workflow.
- **Roll back:** Vercel dashboard → Deployments → pick the last good one → Promote to
  Production. This does not change git — fix forward with a PR.
- **Rotate the token:** create a new token in Vercel, update the `VERCEL_TOKEN` secret,
  then delete the old token.

## Known constraints / lessons

- A failed build cannot take the site down: the job fails and the previous production
  deployment stays live. CI (`checks`) already gates PRs; this is the backstop.
- `concurrency: cancel-in-progress` means a newer `main` supersedes an in-flight deploy.
- The site is fully static (`output: 'static'`), so no `@astrojs/vercel` adapter is
  needed. Adding SSR later would require one.
- `astro.config.mjs` `site:` must match the production origin — it feeds absolute
  canonical/OG URLs and any future sitemap. Update it whenever the domain changes.
```

- [ ] **Step 2: Fix the stale hosting note in `docs/ARCHITECTURE.md`**

Replace this line (in the "Data branches" section):

```
*If we ever migrate hosting:* the data branches are host-independent (they're just git), but a platform that builds every branch needs to be told not to — on Vercel, `git.deploymentEnabled: false`.
```

with:

```
The data branches are host-independent — they are just git, and the browser reads them from raw.githubusercontent.com no matter where the site is hosted. Vercel never builds them because the project's Git integration is disabled: the only thing that deploys is `deploy.yml`, and it only ever deploys `main`.
```

- [ ] **Step 3: Replace the "not yet wired" claim in `docs/ARCHITECTURE.md`**

Replace this line (end of the "CI and releases" section):

```
**Not yet wired: deployment.** The build is green and the pipelines run, but nothing publishes `dist/` to a host.
```

with:

```
`deploy.yml` publishes production on every push to `main` (and on manual dispatch): it installs the Vercel CLI, runs `vercel pull` and `vercel build --prod` (which runs `astro build`), then `vercel deploy --prebuilt --prod`. Vercel's own Git integration is off, so nothing deploys except through this workflow. A failed build leaves the previous production deployment live. See [workflows/deploy.md](../workflows/deploy.md).
```

- [ ] **Step 4: Verify both stale claims are gone**

Run:
```bash
grep -c "Not yet wired" docs/ARCHITECTURE.md; grep -c "git.deploymentEnabled" docs/ARCHITECTURE.md
```
Expected: `0` then `0`

- [ ] **Step 5: Commit**

```bash
git add workflows/deploy.md docs/ARCHITECTURE.md
git commit -m "docs: document the deploy pipeline; correct ARCHITECTURE

ARCHITECTURE said deployment was not wired and recommended a
git.deploymentEnabled toggle that disabling Git integration makes
unnecessary. Both are now false. Adds the deploy SOP alongside the
other pipeline SOPs.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Ship the repo changes

**Files:** none (git/PR operations only)

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: `main` containing the deploy workflow, so Task 6 can dispatch it.

- [ ] **Step 1: Run the full check suite locally, exactly as CI will**

Run:
```bash
npm test && npm run validate && python3 tools/scrapers/build_commitment_index.py --check && python3 -m unittest discover -s tools/tests -p "test_*.py" && npm run build
```
Expected: 21 node tests pass, validator prints `OK: plan/ tree valid`, index prints `in sync`, 40 python tests pass, build prints `28 page(s) built`.

- [ ] **Step 2: Rebase onto the latest main and push**

```bash
git pull --rebase origin main
git push -u origin ci/vercel-deploy
```

- [ ] **Step 3: Open the PR**

```bash
gh pr create --base main --head ci/vercel-deploy \
  --title "ci: deploy to Vercel production from GitHub Actions" \
  --body "Wires production hosting for the July 28 launch, per the spec in docs/superpowers/specs/2026-07-19-vercel-deploy-design.md.

- \`deploy.yml\` — deploys main to Vercel production via the Vercel CLI (pull → build → deploy --prebuilt). Vercel's own Git integration stays off, so the orphan data branches are never built and nothing deploys except this workflow.
- \`vercel.json\` — CORS + cache headers so the /api/*.json open-data endpoints are usable cross-origin.
- \`astro.config.mjs\` — sets the production \`site\` origin (vercel.app for now; flips to the custom domain when DNS is live).
- Docs — adds the deploy SOP and corrects two statements in ARCHITECTURE that this change makes false.

Deploys stay inert until the three Vercel secrets are added; verification steps are in the plan.

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
```

- [ ] **Step 4: Wait for CI, then merge**

```bash
gh pr checks --watch
```
Expected: `checks` passes. Then merge with **Rebase and merge** (repo rule — never squash, never a merge commit).

Note: merging pushes to `main`, which triggers `deploy.yml`. Until the secrets exist the run will fail at `vercel pull` — expected, and harmless. Task 6 makes it pass.

---

### Task 6: Vercel setup and live verification (requires Diego)

The steps in this task that touch the Vercel dashboard, tokens, and GitHub secrets are **Diego's** — the implementer runs only the verification commands afterward.

**Files:** none

**Interfaces:**
- Consumes: the merged workflow from Task 5.
- Produces: a live production site at `https://keikogobierna.vercel.app`.

- [ ] **Step 1 (Diego): create the Vercel project and disable Git integration**

Run `vercel link` locally (or create the project in the dashboard), naming it `keikogobierna` so the generated URL matches the `site` value from Task 2. Then: Project → Settings → Git → disconnect/disable the Git integration.

- [ ] **Step 2 (Diego): add the three repo secrets**

Create a token at Vercel → Account → Settings → Tokens. Then GitHub → Settings → Secrets and variables → Actions → New repository secret, three times:
`VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (the last two are printed by `vercel link` into `.vercel/project.json`).

- [ ] **Step 3: Trigger a deploy and confirm it succeeds**

Run:
```bash
gh workflow run deploy.yml && sleep 20 && gh run list --workflow=deploy.yml --limit 1
```
Then watch it:
```bash
gh run watch "$(gh run list --workflow=deploy.yml --limit 1 --json databaseId -q '.[0].databaseId')"
```
Expected: the run completes with conclusion `success`.

- [ ] **Step 4: Verify the site serves**

Run:
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://keikogobierna.vercel.app/
curl -s https://keikogobierna.vercel.app/ | grep -o "<title>[^<]*</title>"
```
Expected: `200`, and the title `keikogobierna — Seguimiento del plan de gobierno`.

- [ ] **Step 5: Verify the open-data endpoints and their CORS header**

Run:
```bash
curl -sI https://keikogobierna.vercel.app/api/plan.json | grep -iE "^HTTP|access-control-allow-origin|cache-control"
curl -sI https://keikogobierna.vercel.app/api/tracking.json | grep -iE "^HTTP|access-control-allow-origin"
```
Expected: `HTTP/2 200`, `access-control-allow-origin: *`, and a `cache-control` containing `s-maxage=3600`.

- [ ] **Step 6: Verify the Ultimitas runtime fetch works from the deployed origin**

This is the one behavior that cannot be inferred from the build: the page fetches `today.json` from `raw.githubusercontent.com` in the browser. Confirm the data source is reachable and the page ships the fetch:

```bash
curl -s -o /dev/null -w "today.json -> %{http_code}\n" \
  https://raw.githubusercontent.com/DianCotrina/keikogobierna/ultimitas-data/today.json
curl -s https://keikogobierna.vercel.app/ultimitas/ | grep -c "ultimitas-list"
```
Expected: `today.json -> 200` and `1`.

Then open `https://keikogobierna.vercel.app/ultimitas/` in a browser and confirm headlines render (not the skeleton or the error state). A browser check is required here because the rendering happens in client JS.

- [ ] **Step 7: Record the result**

No commit. If every check passed, the site is live on the `vercel.app` URL and the July 28 launch is unblocked even if the domain is not ready.

---

### Task 7: Custom domain cutover (after DNS is live)

Blocked on domain registration and DNS propagation. If this is not done by July 28, launch on the `vercel.app` URL — nothing else depends on it.

**Files:**
- Modify: `astro.config.mjs`
- Modify: `README.md`

**Interfaces:**
- Consumes: the live deployment from Task 6.
- Produces: production served on the custom domain.

- [ ] **Step 1 (Diego): add the domain in Vercel and set DNS**

Project → Settings → Domains → add the registered domain, then create the DNS records Vercel displays at the registrar. Wait for Vercel to report the domain as Valid with an issued certificate.

- [ ] **Step 2: Confirm the domain serves over HTTPS**

Replace `<domain>` with the registered domain:
```bash
curl -s -o /dev/null -w "%{http_code} %{scheme}\n" https://<domain>/
```
Expected: `200 https`

- [ ] **Step 3: Point `site` at the custom domain**

In `astro.config.mjs`, change the `site` line to the registered domain:

```js
  site: 'https://<domain>',
```

- [ ] **Step 4: Add the live URL to `README.md`**

Replace the file contents with:

```markdown
# keikogobierna

Keiko es la siguiente gobernante del perú y esta pagina será para seguir su plan de gobierno actual

**Sitio en vivo:** https://<domain>
```

- [ ] **Step 5: Verify the build still succeeds with the new origin**

Run:
```bash
node -e "import('./astro.config.mjs').then(m => console.log('site =', m.default.site))" && npm run build
```
Expected: `site = https://<domain>` and `28 page(s) built`.

- [ ] **Step 6: Commit, PR, merge**

```bash
git checkout -b ci/custom-domain
git add astro.config.mjs README.md
git commit -m "ci: point the production origin at the custom domain

DNS is live and the certificate has issued, so site: moves off the
vercel.app URL and the README links the live site.

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push -u origin ci/custom-domain
gh pr create --base main --title "ci: point the production origin at the custom domain" --body "DNS is live; moves \`site:\` off the vercel.app URL and links the live site from the README."
```

Merging triggers `deploy.yml`, which republishes with the correct origin.

- [ ] **Step 7: Final check**

```bash
curl -s https://<domain>/ | grep -o "<title>[^<]*</title>"
curl -sI https://<domain>/api/plan.json | grep -iE "^HTTP|access-control-allow-origin"
```
Expected: the Spanish title, `HTTP/2 200`, `access-control-allow-origin: *`.

---

## Plan self-review

**Spec coverage** — every section of the spec maps to a task:

| Spec requirement | Task |
|---|---|
| Git integration OFF (no data-branch builds) | 6 (step 1), documented in 4 |
| `astro.config.mjs` `site:` | 2, flipped in 7 |
| `deploy.yml` (triggers, CLI steps, secrets, concurrency, permissions) | 3 |
| `vercel.json` CORS/cache on `/api/*` | 1, verified in 6 |
| Broken build ⇒ no deploy, previous stays live | Documented in 4; asserted by design in 3 |
| `vercel.app` launch contingency | 6 (site live before any DNS work); 7 optional |
| Manual Vercel/DNS checklist | 4 (SOP) and 6/7 (executable steps) |
| Verification (site, endpoints, CORS, Ultimitas runtime fetch) | 6 steps 4–6 |
| Out of scope: previews, OG image, sitemap, robots, adapter | Not planned — matches spec |

**Placeholder scan** — no TBD/TODO. `<domain>` in Task 7 is a real parameter Diego supplies at cutover time, and every command using it says so.

**Consistency** — `site` is `https://keikogobierna.vercel.app` in Task 2 and every Task 6 URL, and is the only value Task 7 changes. Secret names (`VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`) are identical in Tasks 3, 4, and 6. The job name `production` in Task 3 matches the assertion in its own verification command.
