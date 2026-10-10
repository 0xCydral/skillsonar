---
name: commit-message-writing
description: Write clear commit messages in the Conventional Commits format, with a short imperative subject and a body that explains why the change was made.
---

# Commit message writing

## Subject
`type(scope): summary` in the imperative mood, under 72 characters. Types: feat, fix, docs,
refactor, test, chore.

## Body
Say why, not what; the diff already shows what. Mention the issue number and any behaviour
that changes for users.

## Breaking changes
Add `!` after the type and a `BREAKING CHANGE:` footer.
