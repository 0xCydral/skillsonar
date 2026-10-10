---
name: flaky-test-triage
description: Find and fix tests that pass and fail at random. Reproduce with repeated runs, isolate shared state, remove timing assumptions and quarantine what cannot be fixed yet.
---

# Flaky test triage

## Reproduce
Run the single test in a loop, then the whole file, then the suite in random order. Where it
starts failing tells you whether the cause is the test or its neighbours.

## Common causes
Shared global state, real clocks, network calls, unordered collections and tests that depend
on another test running first.

## Quarantine
Move a test you cannot fix today to a quarantine list with an owner and a deadline.
