"""Command line entry point for invoicelint."""
import argparse
import sys
from pathlib import Path
from typing import List

from .parser import HeaderError, parse_line_items
from .rules import Finding, check_all


def lint_file(path: Path, lenient: bool) -> List[Finding]:
    with path.open(newline="", encoding="utf-8") as stream:
        try:
            items = list(parse_line_items(stream))
        except HeaderError as exc:
            print(f"{path}: {exc}", file=sys.stderr)
            return []
    return check_all(items, lenient=lenient)


def main(argv: List[str] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="invoicelint",
        description="Check invoice line item CSV files for arithmetic and data errors.",
    )
    parser.add_argument("files", nargs="+", type=Path, help="CSV files to check")
    parser.add_argument(
        "--lenient",
        action="store_true",
        help=(
            "downgrade ambiguous findings (missing tax rate, missing currency, "
            "small rounding drift) to warnings instead of errors"
        ),
    )
    args = parser.parse_args(argv)

    had_error = False
    for path in args.files:
        findings = lint_file(path, args.lenient)
        for finding in sorted(findings, key=lambda f: f.line):
            print(f"{path}:{finding}")
            if finding.severity == "error":
                had_error = True

    return 1 if had_error else 0


if __name__ == "__main__":
    sys.exit(main())
