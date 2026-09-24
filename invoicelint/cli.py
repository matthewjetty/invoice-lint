"""Command line entry point for invoicelint."""
import argparse
import json
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


def _finding_to_dict(finding: Finding) -> dict:
    return {
        "line": finding.line,
        "code": finding.code,
        "severity": finding.severity,
        "message": finding.message,
    }


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
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format: text (default) or json, for CI integration",
    )
    args = parser.parse_args(argv)

    had_error = False
    results = []
    for path in args.files:
        findings = sorted(lint_file(path, args.lenient), key=lambda f: f.line)
        if any(finding.severity == "error" for finding in findings):
            had_error = True
        results.append((path, findings))

    if args.format == "json":
        payload = [
            {"file": str(path), "findings": [_finding_to_dict(f) for f in findings]}
            for path, findings in results
        ]
        print(json.dumps(payload, indent=2))
    else:
        for path, findings in results:
            for finding in findings:
                print(f"{path}:{finding}")

    return 1 if had_error else 0


if __name__ == "__main__":
    sys.exit(main())
