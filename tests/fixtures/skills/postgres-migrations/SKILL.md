---
name: postgres-migrations
description: Change a Postgres schema safely on a live database. Add columns without locks, backfill in batches, create indexes concurrently and plan rollbacks.
---

# Postgres migrations

## Safe changes
Add nullable columns first, backfill in small batches, then add the constraint. Create
indexes with `CREATE INDEX CONCURRENTLY`.

## Avoid long locks
Set `lock_timeout` so a migration fails fast instead of queueing behind a long transaction
and blocking every query.

## Rollback
Write the down migration before running the up one, and deploy code that works with both
schemas.
