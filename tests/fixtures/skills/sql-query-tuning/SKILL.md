---
name: sql-query-tuning
description: >
  Speed up slow SQL queries. Read the execution plan with EXPLAIN ANALYZE,
  find sequential scans, add or fix indexes, and rewrite joins that scan
  more rows than they return.
---

# SQL query tuning

## Read the plan
Run `EXPLAIN (ANALYZE, BUFFERS)` on the real query with real data volumes. Compare estimated
rows with actual rows: a large gap means stale statistics.

## Indexes
Add an index for the filter and join columns, in the order the query uses them. Check the
planner actually picks it.

## Rewrites
Replace correlated subqueries with joins, select only the columns you need, and paginate
with keyset conditions instead of large offsets.
