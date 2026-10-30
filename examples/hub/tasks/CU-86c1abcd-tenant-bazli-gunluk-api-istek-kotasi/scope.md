# Scope — CU-86c1abcd

## In scope

backend: the quota check and counter under `app/quota/`, plus its tests.
frontend: the quota indicator in the admin console's usage screen.

## Out of scope

Billing. The plan's quota value is read, never written. Changing how a plan is priced is a
separate task with its own approval path.

## Why these boundaries

Billing is under a change freeze until the next release.
