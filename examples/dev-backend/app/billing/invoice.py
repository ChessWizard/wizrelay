"""Billing. Explicitly denied by this task's scope, and under a change freeze.

Editing this file is what the `pre-edit` hook denies with the pattern `app/billing/**`,
whatever the enforcement mode.
"""

from __future__ import annotations

PLAN_LIMITS = {"free": 100, "pro": 1000, "enterprise": 10000}
