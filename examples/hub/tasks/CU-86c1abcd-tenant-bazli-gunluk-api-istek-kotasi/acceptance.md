# Acceptance criteria — CU-86c1abcd

## AC-1 [backend] A tenant at its daily limit is rejected

Given a tenant whose daily counter equals its plan limit
When the tenant makes one more request
Then the request is rejected with 429 and a Retry-After header
Verification: `pytest -q tests/quota/test_limit.py`

## AC-2 [backend] An accepted request increments the counter

Given a tenant below its limit
When a request is accepted
Then the tenant's daily counter increases by exactly one
Verification: `pytest -q tests/quota/test_counter.py`

## AC-3 [frontend] The remaining quota is visible

Given an admin on the usage screen
When the page loads
Then the remaining daily quota for the tenant is shown
Verification: `npm test -- quota-indicator`
