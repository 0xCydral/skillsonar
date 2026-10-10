---
name: react-testing
description: Write tests for React components with Testing Library and Vitest. Query by role, simulate user events, mock network calls and avoid brittle snapshots.
---

# React testing

## Query like a user
Prefer `getByRole` and `getByLabelText` over test ids. If a role query fails, the component
is probably not accessible, which is worth fixing.

## Interactions
Use `userEvent` rather than `fireEvent`, and `await` every interaction. Wait for async UI
with `findBy` queries instead of arbitrary timeouts.

## Network
Mock requests at the network layer with MSW so the component code stays untouched.
