"""wizrelay — core library.

Layering, enforced by tests/unit/test_architecture.py:

    core      pure functions, no IO
              globs, textformats, schemas, routing, lock, i18n, config, trackers
    services  filesystem and git
              paths, hubrepo, package, audit, context
    entry     command line and hook handlers
              cli, __main__, hooks/*

Runtime code imports only the Python >= 3.9 standard library (an invariant,
asserted by tests/unit/test_stdlib_only.py).
"""

from __future__ import annotations

# Single source of truth is plugin/.claude-plugin/plugin.json; `make release` writes this
# value and tests/unit/test_version.py asserts the three copies agree.
__version__ = "0.1.0"

SCHEMA_VERSION = 1
"""The schema_version every JSON document this project writes carries."""

__all__ = ["SCHEMA_VERSION", "__version__"]
