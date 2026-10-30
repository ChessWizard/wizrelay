#!/usr/bin/env python3
"""Entry point for Claude Code hooks and for `python3 bin/wizrelay.py`.

`hooks/hooks.json` runs this in exec form as `python3 <this file> hook <event>`. Exec form
spawns the interpreter directly with no shell, so a plugin path containing a space stays
one argument and nothing needs quoting.

The only work this file does is put the bundled library on `sys.path`. A plugin is a
directory Claude Code copies into its cache; nothing runs `pip install` for it, so the
import has to work from the checkout as it stands.

Two things have to be true before `import wizrelay` resolves to the bundled package:

* **This file must not shadow it.** Python puts a script's own directory first on
  `sys.path`, and that directory holds this `wizrelay.py`. Left in place, `import wizrelay`
  finds *this launcher* — a module, not a package — and `wizrelay.cli` then fails with
  ``'wizrelay' is not a package``.
* **The bundled library must come first, not merely be present.** An editable install puts
  `plugin/lib` on `sys.path` already, so a membership test would skip the insert and leave
  the script's own directory in front. Precedence is what matters, so the insert is
  unconditional: the bundled copy wins over an older `wizrelay` in site-packages, and the
  plugin's own version is the one whose hook contract matches this `hooks.json`.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_LIB = _HERE.parent / "lib"

sys.path[:] = [entry for entry in sys.path if entry not in ("", str(_HERE))]
sys.path.insert(0, str(_LIB))

from wizrelay.cli import main  # noqa: E402 - the path has to be set up first

if __name__ == "__main__":
    sys.exit(main())
