# Deploy to Vercel (production hosting)

**Date:** 2026-07-19
**Status:** Design approved in conversation (Diego, 2026-07-19); spec review pending

## Problem

The site has never been deployed. `npm run build` produces a static `dist/`, CI is green, the scrapers run — but nothing serves the built site to the public, and the launch deadline is **July 28** (inauguration day). Deployment is the last item on the critical path.

The site must go live on Vercel without disturbing anything already working: the scheduled scraper Actions, the CI `checks` gate, release-please, and the data-branch pattern the Ultimitas page depends on.

## Context — why this is a small change

Reconnaissance of the repo (2026-07-19) found almost no coupling to any host:

- **Static Astro, no adapter, no `vercel.json`, no deploy workflow.** The site has genuinely never been deployed anywhere — there is no GitHub Pages setup to unwind.
- **No `site:` or `base:` in `astro.config.mjs`** — nothing hardcodes a `github.io` URL or a base path.
- **Exactly one runtime data dependency:** `src/components/Ultimitas/ultimitas.ts` fetches `today.json` from `raw.githubusercontent.com`. That is host-independent — it resolves identically from Vercel — so the entire data-branch pattern (`ultimitas-data`, `normas-archive`) carries over untouched.
- The two datos-abiertos endpoints (`/api/plan.json`, `/api/tracking.json`) are rendered to static JSON at build time. No serverless runtime is needed.

The migration is therefore: build the existing static output and serve it from Vercel. No adapter, no SSR, no change to the data pipeline.

## Decisions (approved in conversation)

- **Deploy mechanism: GitHub Actions + Vercel CLI**, not Vercel's Git integration. Keeps all CI/CD in one place (GitHub), consistent with the scrapers, CI, and release-please.
- **Production only for launch.** The workflow deploys `main` → production. No PR preview deploys (a possible fast-follow). Visual review of PRs stays local (`npm run dev` + screenshots), as today.
- **Custom domain, registering in parallel.** The exact name is TBD; Diego registers it separately. The design is parameterized on the domain and works before DNS is live, with the free `*.vercel.app` URL as the launch-day contingency.
- **Static output, no `@astrojs/vercel` adapter.** `output: 'static'` stays.

## Design

### The key move: Vercel Git integration stays OFF

Because deploys are driven by our own workflow via the Vercel CLI, the Vercel project's Git integration is **disabled**. Vercel never watches the repo, so it never attempts to auto-build any branch — including the orphan data branches (`ultimitas-data`, `normas-archive`), which have no `package.json` and would otherwise fail a build. The only thing that ever deploys is `deploy.yml`, deploying `main`.

This is why no `git.deploymentEnabled: false` toggle in `vercel.json` is needed: with integration off, there is nothing to opt out of.

### Data flow — what triggers a deploy

```
PR ──► CI `checks` (must pass) ──► merge to main ──► push event
                                                        │
                                        .github/workflows/deploy.yml
                                                        │
                                    vercel build  (runs npm run build → astro build)
                                                        │
                                    vercel deploy --prebuilt --prod
                                                        │
                                                   production site
```

- A **feature/data PR merging to `main`** triggers a production deploy. In particular a `tracking.json` certification PR redeploys the site — correct, since it changes what the built pages show.
- The **scrapers push to data branches, never to `main`**, so they never trigger a deploy. The Ultimitas page still fetches `today.json` at runtime from `raw.githubusercontent.com`, so fresh headlines appear without any deploy — the whole point of the runtime-fetch design.
- **release-please** PRs merging to `main` also deploy (a release ships the site) — desirable.

### Component 1 — `astro.config.mjs`: set `site:`

Add `site: 'https://<domain>'`. Enables absolute canonical/share-preview URLs and unlocks a sitemap later. Until the domain is registered, `site:` points at the `*.vercel.app` URL; flipping it to the custom domain is a one-line PR once DNS is live.

### Component 2 — `.github/workflows/deploy.yml`

- **Triggers:** `on: push: branches: [main]` (production deploy) + `workflow_dispatch` (manual redeploy).
- **Steps (canonical Vercel-CLI pattern):**
  1. `actions/checkout@v4`
  2. `actions/setup-node@v4` (node 22, npm cache)
  3. `npm install --global vercel@latest`
  4. `vercel pull --yes --environment=production --token=$VERCEL_TOKEN`
  5. `vercel build --prod --token=$VERCEL_TOKEN` — runs the project build (`npm run build` → `astro build`) and packages `dist/` into `.vercel/output`.
  6. `vercel deploy --prebuilt --prod --token=$VERCEL_TOKEN` — deploys the prebuilt output.
- **Auth/env:** `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` from repo secrets (the org/project ids as `env:` so the CLI reads them).
- **`permissions:`** none beyond default (this workflow only calls Vercel, touches no GitHub API).
- **`concurrency:`** group on the workflow with `cancel-in-progress: true`, so rapid successive merges don't race two deploys.

### Component 3 — `vercel.json` (minimal)

One purpose: CORS + cache headers on the datos-abiertos endpoints, so `/api/plan.json` and `/api/tracking.json` are usable cross-origin (they already declare an open-data license, so third parties should be able to fetch them from a browser).

```json
{
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

This is the only addition beyond bare static hosting. If review prefers, it can be deferred to a fast-follow — hosting works without it; only cross-origin fetches of the JSON endpoints are affected.

## Error handling & contingency

- **Broken build = no deploy.** If `astro build` fails inside `vercel build`, the deploy job fails and the *previous* production deployment stays live. A bad merge cannot take the site down. CI already gates PRs; this is the backstop.
- **DNS not propagated by July 28** → the `*.vercel.app` URL is already live and shareable. Launch on it, and flip the custom domain the moment its certificate issues. The only code change is the one-line `site:` update.

## Manual steps (Diego — Vercel dashboard / DNS)

These cannot be done from the repo. Written as a checklist for launch:

1. Register the domain.
2. Create the Vercel project (`vercel link` locally, or via dashboard) → yields `VERCEL_ORG_ID` + `VERCEL_PROJECT_ID`.
3. **Turn off Git integration** for the project (Project → Settings → Git → Disconnect / disable).
4. Generate a `VERCEL_TOKEN` (Account → Settings → Tokens).
5. Add three repo secrets in GitHub (Settings → Secrets → Actions): `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
6. Add the domain in Vercel (Project → Settings → Domains) and set the DNS records it shows at the registrar.

## Verification

- **After secrets are added:** `workflow_dispatch` the deploy workflow → the run succeeds and the site loads on the `*.vercel.app` URL.
- **Runtime data:** the Ultimitas page fetches `today.json` and renders headlines from the deployed origin (confirms the `raw.githubusercontent.com` fetch works cross-origin from Vercel).
- **Open data:** `curl -I` on `/api/plan.json` and `/api/tracking.json` returns 200 with `Access-Control-Allow-Origin: *`.
- **Full build parity:** `npm test`, `npm run validate`, and `npm run build` remain green (unaffected by the added files).
- **Post-domain:** the custom domain serves over HTTPS (Vercel-issued cert) and `site:` reflects it.

## Out of scope (deliberate — not needed to go live)

- **PR preview deploys** — possible fast-follow; needs added workflow paths (preview vs prod) and a per-PR Vercel build.
- **OG share image, sitemap, `robots.txt`** — genuine improvements for a site meant to be shared, but independent of hosting. Setting `site:` here makes the sitemap a trivial later add.
- **`@astrojs/vercel` adapter / SSR / serverless** — not needed; the site is fully static.
- **Migrating the data branches off `raw.githubusercontent.com`** — they are host-independent and work as-is; no reason to change at launch.

## Decisions log (conversation, 2026-07-19)

- Deploy via **GitHub Actions + Vercel CLI**, not Vercel Git integration — keep CI/CD unified on GitHub. Side effect: Git integration OFF removes the data-branch build hazard entirely.
- **Production-only** deploys for launch; PR previews deferred.
- **Custom domain**, registered in parallel; parameterize on it; `*.vercel.app` is the launch contingency.
- `vercel.json` limited to **CORS/cache headers on `/api/*`**; flagged for review as optionally a fast-follow.
