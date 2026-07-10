# Semver Releases Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** release-please automation, CI gate on PRs, and the site version in the footer.

**Architecture:** Two GitHub Actions workflows plus a one-line build-time JSON import in the layout. Full file contents specified in the spec — this plan sequences and verifies them.

**Spec:** `docs/superpowers/specs/2026-07-09-semver-releases-design.md` (contains the exact workflow definitions and footer snippet).

## Global Constraints

- Branch `semver-releases` off current main; commits end with the Claude co-author trailer; rebase-and-merge flow.
- Footer text stays language-neutral (`vX.Y.Z`); tooltip in Spanish.

### Task 1: workflows + footer version

- [ ] Create `.github/workflows/release-please.yml` per spec §1 (googleapis/release-please-action@v4, release-type node, contents+PR write permissions).
- [ ] Create `.github/workflows/ci.yml` per spec §3 (pull_request → npm ci, test, validate, build; Node 22 with npm cache).
- [ ] Add `import pkg from '../../package.json';` to `Base.astro` frontmatter and the release-link version line under the footer disclaimer per spec §2.
- [ ] `npm run build` passes; screenshot footer shows `v1.0.0`.
- [ ] Commit, push, PR.

### Task 2: post-merge verification (after PR merges)

- [ ] `gh run list` shows the workflows parsed and ran.
- [ ] release-please opens its release PR on the next main push; merging it produces tag + GitHub Release (pin first release to v1.0.0 if desired).
