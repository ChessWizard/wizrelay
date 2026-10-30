# Decisions — CU-86c1abcd

## D-001 Fail open when Redis is unavailable (v1, 2026-10-30)

- Question: What happens to a request when the counter store cannot be reached?
- Decision: Allow the request and log a warning. The quota is a cost control, not a safety
  control, so an outage must not stop customer traffic.
- Rationale: A hard failure converts a Redis incident into an API outage.
- Impact: AC-1 applies only when the counter is readable.

## D-002 Retry-After is capped at one hour (v2, 2026-10-30)

- Question: Q-001 — what upper bound applies to Retry-After?
- Decision: Cap it at 3600 seconds.
- Rationale: A longer value makes clients look stuck.
- Impact: AC-1 and the contract in contracts.md.
