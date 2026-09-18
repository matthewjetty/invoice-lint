"""CSV parsing for invoice line item files.

Expected columns: description, quantity, unit_price, tax_rate, line_total,
currency. Extra columns are ignored so callers can pass through whatever
export their billing system produces. tax_rate and currency may be blank;
whether that is an error or just a warning is decided by the rules, not
the parser.
"""
import csv
from dataclasses import dataclass
from typing import Iterator, TextIO

REQUIRED_COLUMNS = ("description", "quantity", "unit_price", "line_total")


@dataclass
class RawLineItem:
    line_number: int
    description: str
    quantity: str
    unit_price: str
    tax_rate: str
    line_total: str
    currency: str


class HeaderError(Exception):
    """Raised when the CSV header is missing required columns."""


def parse_line_items(stream: TextIO) -> Iterator[RawLineItem]:
    reader = csv.DictReader(stream)
    if reader.fieldnames is None:
        raise HeaderError("file is empty, expected a header row")

    missing = [c for c in REQUIRED_COLUMNS if c not in reader.fieldnames]
    if missing:
        raise HeaderError(f"missing required column(s): {', '.join(missing)}")

    # DictReader.line_num counts the header row, so the first data row is 2,
    # matching what a reader would see if they opened the file in an editor.
    for row in reader:
        yield RawLineItem(
            line_number=reader.line_num,
            description=(row.get("description") or "").strip(),
            quantity=(row.get("quantity") or "").strip(),
            unit_price=(row.get("unit_price") or "").strip(),
            tax_rate=(row.get("tax_rate") or "").strip(),
            line_total=(row.get("line_total") or "").strip(),
            currency=(row.get("currency") or "").strip(),
        )
