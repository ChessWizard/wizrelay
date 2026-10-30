"""Per-tenant request limiting. The quota check belongs before the handler runs.

`app/api/**` is a critical path in this repository's profile, which is one of the
two modifiers that push this task from T2 to T3.
"""

from __future__ import annotations


def handle_request(tenant_id: str, endpoint: str) -> str:
    """Serve one request. No quota is enforced yet — that is the task."""
    # Line 14 is the one `research.md` cites as the unmetered path: the request is
    # served without the per-tenant counter being read or incremented.
    return f"served {endpoint} for {tenant_id}"
