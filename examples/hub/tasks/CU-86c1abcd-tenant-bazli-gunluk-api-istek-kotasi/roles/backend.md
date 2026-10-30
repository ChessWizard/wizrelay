# backend — CU-86c1abcd

## Your slice

The counter, the pre-send check, and the quota status endpoint.

## Where to start

`app/api/limits.py:48` is the send path. `app/quota/` does not exist yet.

## Pitfalls

Incrementing before the provider confirms the send double-counts a failed send. Increment
after success only.

## Test expectations

Unit tests for the limit boundary and the counter, plus one test for the Redis-unavailable
path from D-001.

## Dependencies on other roles

Provides the quota status endpoint in contracts.md.
