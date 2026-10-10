---
name: regex-builder
description: Write and debug regular expressions. Build a pattern from examples, explain what it matches, and avoid catastrophic backtracking.
---

# Regex builder

## From examples
Collect strings that must match and strings that must not. Start simple, then tighten until
every negative example fails.

## Explain
Break the pattern into groups and say in words what each one matches. Use named groups.

## Performance
Nested quantifiers like `(a+)+` can backtrack exponentially. Prefer possessive or atomic
forms, or anchor the pattern.
