#!/usr/bin/env python3
"""Entry point for Claude Code hooks and for `python3 bin/wizrelay.py`.

`hooks/hooks.json` runs this in exec form as `python3 <this file> hook <event>`
. Exec form spawns the interpreter directly with no shell, so a plugin path
containing a space stays one argument and nothing needs quoting.

The only work this file does is put the bundled library on `sys.path`. A plugin is a
directory Claude Code copies into its cache; nothing runs `pip install` for it, so the
import has to work from the checkout as it stands.

`sys.path.insert(0, ...)` is deliberate: the bundled copy must win over an older
`wizrelay` that happens to be installed in the interpreter's site-packages. The plugin's
own version is the one whose hook contract matches this `hooks.json`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parent.parent / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from wizrelay.cli import main  # noqa: E402 - the path has to be set up first

if __name__ == "__main__":
    sys.exit(main())
