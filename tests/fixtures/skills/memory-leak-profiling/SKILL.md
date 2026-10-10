---
name: memory-leak-profiling
description: Find memory leaks in long-running Node.js and Python services. Take heap snapshots, compare them over time and trace retained objects to their owner.
---

# Memory leak profiling

## Confirm the leak
Plot resident memory over hours. A leak is growth that survives garbage collection, not a
spike.

## Snapshots
Take a heap snapshot, run the workload, take a second one and diff them. The types with the
largest retained size growth are the suspects.

## Trace
Follow the retaining path to the owner: an unbounded cache, a listener never removed or a
global list.
