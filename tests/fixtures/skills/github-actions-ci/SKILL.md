---
name: github-actions-ci
description: Build continuous integration workflows with GitHub Actions. Test matrices, dependency caching, reusable workflows and secrets handling for pull requests.
---

# GitHub Actions CI

## Workflow shape
Trigger on `pull_request` and pushes to main. One job per concern: lint, test, build.

## Matrix and cache
Test across operating systems and language versions with `strategy.matrix`. Cache the
package manager directory keyed on the lockfile hash.

## Secrets
Never print secrets. Forked pull requests do not receive them, so keep tests independent
of credentials.
