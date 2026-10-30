#!/usr/bin/env python3
"""Assert the core modules reach the project's coverage floor.

`pytest --cov-fail-under` covers the whole package (>= 80%). The core modules carry a
higher bar (>= 90%), so this script reads the Cobertura report pytest-cov wrote and checks
that subset separately. Exit code 1 means the gate failed.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

# The pure, IO-free layer.
CORE_MODULES = frozenset(
    {
        "config.py",
        "globs.py",
        "i18n.py",
        "lock.py",
        "routing.py",
        "schemas.py",
        "textformats.py",
        "trackers.py",
    }
)
FLOOR = 90.0


def main() -> int:
    report = Path("coverage.xml")
    if not report.exists():
        print("coverage.xml not found; run `make cov` first.", file=sys.stderr)
        return 1

    root = ET.parse(report).getroot()  # noqa: S314 - our own generated report
    hits = 0
    total = 0
    seen: set[str] = set()

    for cls in root.iter("class"):
        filename = cls.get("filename") or ""
        name = Path(filename).name
        if name not in CORE_MODULES:
            continue
        seen.add(name)
        for line in cls.iter("line"):
            total += 1
            if (line.get("hits") or "0") != "0":
                hits += 1

    missing = sorted(CORE_MODULES - seen)
    if missing:
        print(f"core modules missing from the coverage report: {', '.join(missing)}")

    if total == 0:
        print("no core statements found in coverage.xml", file=sys.stderr)
        return 1

    percent = 100.0 * hits / total
    verdict = "ok" if percent >= FLOOR else "FAIL"
    print(f"core coverage: {percent:.2f}% of {total} statements (floor {FLOOR:.0f}%) [{verdict}]")
    return 0 if percent >= FLOOR else 1


if __name__ == "__main__":
    sys.exit(main())
