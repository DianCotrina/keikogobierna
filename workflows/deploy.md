# Workflow: Production deploy (Vercel Git integration)

## Objective

Publish the built site to Vercel production. Unlike every other pipeline here — which
either files review issues or publishes to a data branch — this one serves the public
site itself, at https://www.keikogobierna.com (the apex 308-redirects to www).

## How it works

Vercel's **Git integration** watches the GitHub repo directly — there is no deploy
workflow in `.github/workflows/` and no Vercel secrets in the repo:

1. **Push to `main`** (any merged PR, including release-please's version bump) →
   Vercel builds (`npm run build` → `astro build`) and deploys to **production**.
2. **Every PR** gets a **preview deployment**; the Vercel bot links it on the PR.
3. **Data branches never deploy**: `vercel.json` sets
   `git.deploymentEnabled: { "ultimitas-data": false, "normas-archive": false }`,
   so the scrapers' 4×/day pushes are invisible to Vercel.

A `tracking.json` certification PR merging to `main` republishes the site with the new
status — that is the intent. Scraper runs need **no deploy**: the Ultimitas page fetches
`today.json` from `raw.githubusercontent.com` at runtime.

Decision log: an Actions+CLI pipeline (`deploy.yml`) was built first per the spec
(`docs/superpowers/specs/2026-07-19-vercel-deploy-design.md`), but the Git integration
was connected during launch (2026-07-19), worked, and was kept; `deploy.yml` was removed
rather than run both paths. The three `VERCEL_*` repo secrets it needed were never created.

## Operations

- **Manual redeploy:** Vercel dashboard → Deployments → ⋯ on the latest → Redeploy.
- **Roll back:** Vercel dashboard → Deployments → pick the last good one → Promote to
  Production. This does not change git — fix forward with a PR.
- **Domain/DNS:** registered at Hostinger (WHOIS privacy on); DNS stays on Hostinger
  nameservers with A/CNAME records pointing at Vercel. Managed in Vercel → Settings →
  Domains and Hostinger hPanel → DNS.

## Known constraints / lessons

- A broken build cannot take the site down: the failed deployment never goes live and
  the previous production deployment keeps serving. CI (`checks`) already gates PRs.
- The site is fully static (`output: 'static'`); no `@astrojs/vercel` adapter. Adding
  SSR later would require one.
- `astro.config.mjs` `site:` must match the production origin
  (`https://www.keikogobierna.com`) — it feeds absolute canonical/OG URLs and any
  future sitemap. Update it if the domain ever changes.
- `vercel.json` also sets CORS + cache headers on `/api/*` (the open-data endpoints);
  verify with `curl -sI https://www.keikogobierna.com/api/plan.json` after changing it.
