from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, ROUND_HALF_UP


_LOCALE_RULES: dict[str, dict[str, str]] = {
    "en": {
        "decimal": ".",
        "thousands": ",",
        "date": "{month}/{day}/{year}",
        "time": "{hour12}:{minute:02d} {ampm}",
        "datetime": "{date} {time}",
    },
    "fr": {
        "decimal": ",",
        "thousands": " ",
        "date": "{day}/{month}/{year}",
        "time": "{hour24}:{minute:02d}",
        "datetime": "{date} {time}",
    },
    "ar": {
        "decimal": ".",
        "thousands": ",",
        "date": "{day}/{month}/{year}",
        "time": "{hour24}:{minute:02d}",
        "datetime": "{date} {time}",
    },
}


@dataclass(frozen=True)
class LocaleRule:
    decimal_separator: str
    thousands_separator: str
    date_pattern: str
    time_pattern: str
    datetime_pattern: str


def locale_rule(locale: str) -> LocaleRule:
    key = _normalize_locale(locale)
    raw = _LOCALE_RULES.get(key, _LOCALE_RULES["en"])
    return LocaleRule(
        decimal_separator=raw["decimal"],
        thousands_separator=raw["thousands"],
        date_pattern=raw["date"],
        time_pattern=raw["time"],
        datetime_pattern=raw["datetime"],
    )


def format_number(value: int | float | Decimal, *, locale: str = "en", precision: int = 2) -> str:
    rule = locale_rule(locale)
    quantized = Decimal(str(value)).quantize(Decimal(f"1.{'0' * max(0, precision)}"), rounding=ROUND_HALF_UP)
    sign = "-" if quantized < 0 else ""
    quantized = abs(quantized)
    integer_part, _, decimal_part = f"{quantized:f}".partition(".")
    grouped = _group_thousands(integer_part, separator=rule.thousands_separator)
    if precision <= 0:
        return f"{sign}{grouped}"
    decimal_text = (decimal_part + ("0" * precision))[:precision]
    return f"{sign}{grouped}{rule.decimal_separator}{decimal_text}"


def format_date(value: date | datetime, *, locale: str = "en") -> str:
    rule = locale_rule(locale)
    if isinstance(value, datetime):
        value = value.date()
    return rule.date_pattern.format(day=value.day, month=value.month, year=value.year)


def format_time(value: time | datetime, *, locale: str = "en") -> str:
    rule = locale_rule(locale)
    if isinstance(value, datetime):
        value = value.time()
    hour24 = value.hour
    hour12 = 12 if hour24 % 12 == 0 else hour24 % 12
    ampm = "AM" if hour24 < 12 else "PM"
    return rule.time_pattern.format(hour24=hour24, hour12=hour12, minute=value.minute, ampm=ampm)


def format_datetime(value: datetime, *, locale: str = "en") -> str:
    rule = locale_rule(locale)
    date_text = format_date(value, locale=locale)
    time_text = format_time(value, locale=locale)
    return rule.datetime_pattern.format(date=date_text, time=time_text)


def _normalize_locale(locale: str) -> str:
    value = str(locale or "en").strip().replace("_", "-").lower()
    if not value:
        return "en"
    language = value.split("-", 1)[0]
    return language or "en"


def _group_thousands(text: str, *, separator: str) -> str:
    if len(text) <= 3:
        return text
    chunks: list[str] = []
    remaining = text
    while remaining:
        chunks.append(remaining[-3:])
        remaining = remaining[:-3]
    return separator.join(reversed(chunks))


__all__ = [
    "LocaleRule",
    "format_date",
    "format_datetime",
    "format_number",
    "format_time",
    "locale_rule",
]
