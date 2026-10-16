"""Coverage gates (IMPLEMENTATION §6): ≥ 85 % overall, ≥ 95 % for critical modules.

Usage: python coverage_gate.py reports/coverage.json [--total 85] [--critical 95]

Critical modules are the services and policies of access, audit, billing,
payments and insurance — including the access decision modules (chart access,
break-glass, care teams, approvals, assignments); they are checked once they exist.
"""

import argparse
import json
import re
import sys
from pathlib import Path

CRITICAL = re.compile(
    r"^apps[\\/](access|audit|billing|payments|insurance)[\\/]"
    r"(services|policies|approvals|assignments|chart|breakglass|care_team)\.py$"
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--total", type=float, default=85.0)
    parser.add_argument("--critical", type=float, default=95.0)
    args = parser.parse_args()

    data = json.loads(args.report.read_text(encoding="utf-8"))
    failures = []
    total = data["totals"]["percent_covered"]
    if total < args.total:
        failures.append(f"overall coverage {total:.1f}% < {args.total:.0f}%")

    for name, info in sorted(data["files"].items()):
        if CRITICAL.match(name):
            percent = info["summary"]["percent_covered"]
            status = "ok" if percent >= args.critical else "FAIL"
            print(f"critical {status:4} {percent:5.1f}%  {name}")
            if percent < args.critical:
                failures.append(f"{name} coverage {percent:.1f}% < {args.critical:.0f}%")

    print(f"overall coverage {total:.1f}% (gate {args.total:.0f}%)")
    for failure in failures:
        print(f"coverage gate: {failure}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
