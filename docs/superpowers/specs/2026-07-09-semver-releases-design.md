# Semantic versioning and releases

**Date:** 2026-07-09
**Status:** Approved by Diego (design conversation, 2026-07-09)

## Problem

The site deploys soon. There is no versioning today: `package.json` is frozen at 1.0.0, no git tags, no changelog, no CI. Deployed revisions need identifiable versions.

## Design

### 1. release-please workflow

`.github/workflows/release-please.yml` — on every push to `main`, `googleapis/release-please-action@v4` with `release-type: node`:

- Parses conventional commits since the last release (the repo already uses `feat:`/`fix:`/`docs:`/`refactor:`).
- Maintains one always-open release PR with the `package.json` bump and generated `CHANGELOG.md` (`feat:` → minor, `fix:` → patch, `feat!`/`BREAKING CHANGE:` → major).
- Merging the release PR (rebase-and-merge, per the repo git workflow) tags `vX.Y.Z` and publishes a GitHub Release.
- Permissions: `contents: write`, `pull-requests: write`; uses the default `GITHUB_TOKEN`.
- Known limitation, accepted: PRs created by `GITHUB_TOKEN` don't trigger other workflows, so the CI check won't run on the release PR itself (it only touches version metadata).
- First release: the initial release PR is editable — pin it to `v1.0.0` for the first deployment if release-please proposes something else.

### 2. Version in the site footer

`Base.astro` imports `package.json` (static JSON import, same rationale as `plan.mjs`) and renders in the footer, under the disclaimer text:

```astro
<a href="https://github.com/DianCotrina/keikogobierna/releases" target="_blank" rel="noopener noreferrer"
   class="nav-link font-mono text-[0.65rem] text-tintafina" title="Historial de versiones">v{pkg.version}</a>
```

Visitor-facing text is just `vX.Y.Z` (language-neutral); the tooltip is Spanish.

### 3. CI workflow

`.github/workflows/ci.yml` — on `pull_request`: checkout, setup-node (Node 22, npm cache), `npm ci`, `npm test`, `npm run validate` (ubuntu ships python3), `npm run build`. Gates PRs on green before they can reach main/releases.

## Out of scope

- Deployment/hosting workflow (own design later; it will consume these tags).
- Publishing to npm (this is a website, not a package).

## Verification

- Local: `npm run build` passes; footer shows `v1.0.0` in a screenshot; `npm ci` works against the committed lockfile.
- Workflow YAML: validated by pushing the branch and checking `gh run list` / the Actions tab for parse errors (workflows only execute on GitHub).
- End-to-end: after this PR merges, confirm release-please opens its release PR on the next push to main; merge it and confirm tag + GitHub Release exist.
