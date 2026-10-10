---
name: kubernetes-pod-debugging
description: Diagnose Kubernetes pods that crash, restart repeatedly or stay Pending. Covers kubectl describe, logs, events, OOMKilled and CrashLoopBackOff.
---

# Kubernetes pod debugging

## Check the pod first
Run `kubectl get pod -o wide` and `kubectl describe pod <name>`. Read the Events section
from the bottom up: scheduling failures, image pull errors and failed probes show up there.

## Crashes and restarts
Use `kubectl logs <pod> --previous` to read the last crashed container. A restart count that
keeps climbing with exit code 137 means the container was OOMKilled: raise the memory limit or
fix the leak.

## Pending pods
Look for insufficient CPU or memory, unbound volume claims and node taints.
