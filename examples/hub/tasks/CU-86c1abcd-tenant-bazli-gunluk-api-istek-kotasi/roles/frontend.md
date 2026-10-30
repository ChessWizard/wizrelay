# frontend — CU-86c1abcd

## Your slice

The quota indicator on the usage screen.

## Where to start

`src/features/usage/UsageScreen.tsx` holds the screen layout.

## Pitfalls

Do not compute `remaining` in the client; the endpoint already returns it, and a local
calculation drifts when the reset window changes.

## Test expectations

A component test for the loaded, loading and error states.

## Dependencies on other roles

Consumes the quota status endpoint in contracts.md.
