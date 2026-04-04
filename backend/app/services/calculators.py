from __future__ import annotations

from datetime import date, timedelta


def calculate_court_fee(claim_amount_uah: float, rate: float = 0.015, min_fee_uah: float = 1211.20) -> float:
    calculated = claim_amount_uah * rate
    return round(max(calculated, min_fee_uah), 2)


def calculate_penalty(
    principal_uah: float,
    debt_start_date: date,
    debt_end_date: date,
    annual_rate: float = 0.03,
) -> float:
    days = max((debt_end_date - debt_start_date).days, 0)
    penalty = principal_uah * annual_rate * days / 365
    return round(penalty, 2)


def calculate_deadline(start_date: date, days: int) -> date:
    return start_date + timedelta(days=days)


def calculate_limitation_deadline(violation_date: date, years: int = 3) -> date:
    return violation_date.replace(year=violation_date.year + years)
