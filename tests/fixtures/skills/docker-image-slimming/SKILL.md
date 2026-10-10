---
name: docker-image-slimming
description: Shrink Docker images and speed up builds with multi-stage Dockerfiles, a small base image, layer ordering for cache hits and a proper .dockerignore.
---

# Docker image slimming

## Multi-stage builds
Compile in a build stage and copy only the artifact into a minimal runtime stage.

## Layer cache
Copy dependency manifests first and install, then copy the source. A source change then
reuses the cached dependency layer.

## Trim
Use slim or distroless bases, remove package manager caches in the same layer that creates
them, and list node_modules, .git and test data in `.dockerignore`.
