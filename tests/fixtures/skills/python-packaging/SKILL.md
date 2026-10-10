---
name: python-packaging
description: Package a Python project with pyproject.toml, build sdist and wheel files, version releases and publish to PyPI with trusted publishing.
---

# Python packaging

## Metadata
Declare the project in `pyproject.toml`: name, version, dependencies, entry points under
`[project.scripts]` and the build backend.

## Build
Run `python -m build` and install the wheel into a clean virtualenv to check it works
outside the source tree.

## Publish
Upload with `twine`, or use trusted publishing from CI so no token is stored.
