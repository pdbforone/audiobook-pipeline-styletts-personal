from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .advisor import generate_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Policy Engine CLI")
    sub = parser.add_subparsers(dest="command")

    report_cmd = sub.add_parser("report", help="Generate policy summary report")
    report_cmd.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional report path (defaults to policy_reports/summary.md)",
    )

    args = parser.parse_args(argv)
    if args.command == "report":
        path = generate_report(Path(args.output) if args.output else None)
        print(f"Policy report written to {path}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
