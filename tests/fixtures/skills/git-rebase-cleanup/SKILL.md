---
name: git-rebase-cleanup
description: |
  Rewrite messy branch history before review. Use interactive rebase to squash
  fixup commits, reorder changes, reword messages and resolve conflicts that
  appear while replaying commits.
---

# Git rebase cleanup

## Before you start
Create a backup branch with `git branch backup/<name>`. Never rewrite history that others
have already pulled.

## Squash and reorder
Run `git rebase -i <base>`. Mark noise commits as `fixup`, move related commits next to each
other, and change `pick` to `reword` where the message is unclear.

## Conflicts
Fix the files, `git add` them and run `git rebase --continue`. If it goes wrong,
`git rebase --abort` returns the branch to where it was.
