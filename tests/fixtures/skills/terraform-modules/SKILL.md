---
name: terraform-modules
description: Structure Terraform code into reusable modules, manage remote state and locking, and investigate drift between the plan and real infrastructure.
---

# Terraform modules

## Layout
One module per concern: network, database, compute. Expose only the variables callers need
and document every output.

## State
Keep state in a remote backend with locking. Never edit the state file by hand; use
`terraform state mv` and `terraform import`.

## Drift
Run `terraform plan -refresh-only` to see what changed outside of Terraform before applying.
