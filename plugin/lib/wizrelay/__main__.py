"""`python -m wizrelay` — the same entry point as the console script.

Having this module means the package works without being installed: the hook launcher
puts `plugin/lib` on `sys.path` and runs `python3 -m wizrelay`, so no `pip install` step
stands between a freshly installed plugin and a working hook.
"""

from __future__ import annotations

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
