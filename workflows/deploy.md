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
