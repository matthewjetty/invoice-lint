"""Checks applied to each parsed invoice line item.

Strict mode is the default: anything ambiguous (missing tax rate, missing
currency, arithmetic that's off by a rounding hair) is reported as an error.
--lenient downgrades those specific cases to warnings and widens the
rounding tolerance, for people stuck importing exports they don't control.
Things that are just wrong (negative unit price, unparsable numbers) stay
errors in both modes.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable, List, Optional

from .parser import RawLineItem

STRICT_TOLERANCE = Decimal("0.00")
LENIENT_TOLERANCE = Decimal("0.02")

# Not exhaustive, just enough to flag obvious typos like "USSD" or "usd".
KNOWN_CURRENCY_CODES = {
    "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF", "NZD", "SEK", "NOK",
    "DKK", "PLN", "CZK", "HUF", "MXN", "BRL", "INR", "CNY", "SGD", "HKD",
}


@dataclass
class Finding:
    line: int
    code: str
    severity: str  # "error" or "warning"
    message: str

    def __str__(self) -> str:
        return f"{self.line}: {self.severity} {self.code}: {self.message}"


def _parse_decimal(raw: str) -> Optional[Decimal]:
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def check_line_item(item: RawLineItem, lenient: bool = False) -> List[Finding]:
    findings: List[Finding] = []
    line = item.line_number

    if not item.description:
        findings.append(Finding(line, "E001", "error", "description is empty"))

    quantity = _parse_decimal(item.quantity)
    if quantity is None:
        findings.append(Finding(line, "E002", "error", f"quantity {item.quantity!r} is not a number"))
    elif quantity < 0:
        findings.append(Finding(line, "E003", "error", f"quantity {quantity} is negative"))

    unit_price = _parse_decimal(item.unit_price)
    if unit_price is None:
        findings.append(Finding(line, "E004", "error", f"unit_price {item.unit_price!r} is not a number"))
    elif unit_price < 0:
        findings.append(Finding(line, "E005", "error", f"unit_price {unit_price} is negative"))

    line_total = _parse_decimal(item.line_total)
    if line_total is None:
        findings.append(Finding(line, "E006", "error", f"line_total {item.line_total!r} is not a number"))

    if item.tax_rate:
        tax_rate = _parse_decimal(item.tax_rate)
        if tax_rate is None:
            findings.append(Finding(line, "E007", "error", f"tax_rate {item.tax_rate!r} is not a number"))
        elif tax_rate < 0:
            findings.append(Finding(line, "E008", "error", f"tax_rate {tax_rate} is negative"))
    else:
        tax_rate = Decimal("0")
        findings.append(Finding(
            line, "W001", "warning" if lenient else "error",
            "tax_rate is missing, assuming 0",
        ))

    if item.currency:
        if len(item.currency) != 3 or item.currency.upper() != item.currency:
            findings.append(Finding(
                line, "E009", "error",
                f"currency {item.currency!r} is not a 3-letter uppercase code",
            ))
        elif item.currency not in KNOWN_CURRENCY_CODES:
            findings.append(Finding(
                line, "W002", "warning",
                f"currency {item.currency!r} is not in the known code list",
            ))
    else:
        findings.append(Finding(
            line, "W003", "warning" if lenient else "error",
            "currency is missing",
        ))

    if quantity is not None and unit_price is not None and line_total is not None and tax_rate is not None:
        expected = (quantity * unit_price * (Decimal("1") + tax_rate)).quantize(Decimal("0.01"))
        tolerance = LENIENT_TOLERANCE if lenient else STRICT_TOLERANCE
        if abs(expected - line_total) > tolerance:
            findings.append(Finding(
                line, "E010", "error",
                f"line_total {line_total} does not match quantity * unit_price * "
                f"(1 + tax_rate) = {expected}",
            ))

    return findings


def check_all(items: Iterable[RawLineItem], lenient: bool = False) -> List[Finding]:
    findings: List[Finding] = []
    for item in items:
        findings.extend(check_line_item(item, lenient=lenient))
    return findings
