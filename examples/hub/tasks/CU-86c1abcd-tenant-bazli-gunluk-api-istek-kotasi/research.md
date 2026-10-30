# Research — CU-86c1abcd

## Problem

Tenants can call the API with no daily limit at all. A single misconfigured tenant
exhausted the shared upstream quota last month and blocked every other tenant.

## Current state, with evidence

`app/api/limits.py:48` serves requests without any per-tenant counter. The only limit is the
provider's global rate limit, enforced in `app/api/client.py:112`.

## Approach

A per-tenant daily counter in Redis, checked before the send and incremented after a
successful one. The limit comes from the tenant's plan.

## Alternatives rejected

| Alternative | Why not |
|---|---|
| Postgres counter | A write per message on the hot path; Redis already carries session state. |
| Provider-side quota | The provider bills per account, not per tenant. |

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Redis unavailable | Sends fail closed or open | Fail open and log; a quota is not a safety control. |
