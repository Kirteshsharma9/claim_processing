from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class Money:
    """Immutable monetary value using Decimal for precision."""
    amount: Decimal

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")
        object.__setattr__(self, 'amount', self.amount.quantize(Decimal('0.01')))

    @classmethod
    def zero(cls) -> "Money":
        return cls(Decimal("0.00"))

    @classmethod
    def from_float(cls, value: float) -> "Money":
        return cls(Decimal(str(value)))

    def __add__(self, other: "Money") -> "Money":
        return Money(self.amount + other.amount)

    def __sub__(self, other: "Money") -> "Money":
        return Money(self.amount - other.amount)

    def __mul__(self, factor: float) -> "Money":
        return Money(self.amount * Decimal(str(factor)))

    def __lt__(self, other: "Money") -> bool:
        return self.amount < other.amount

    def __le__(self, other: "Money") -> bool:
        return self.amount <= other.amount

    def __gt__(self, other: "Money") -> bool:
        return self.amount > other.amount

    def __ge__(self, other: "Money") -> bool:
        return self.amount >= other.amount


@dataclass(frozen=True)
class DateRange:
    """Immutable date range with start and end dates."""
    start: date
    end: Optional[date] = None

    def __post_init__(self):
        if self.end is not None and self.end < self.start:
            raise ValueError("End date cannot be before start date")

    def contains(self, target: date) -> bool:
        """Check if a date falls within this range."""
        if self.end is None:
            return target >= self.start
        return self.start <= target <= self.end

    @classmethod
    def calendar_year(cls, year: int) -> "DateRange":
        """Create a date range for a full calendar year."""
        return cls(
            start=date(year, 1, 1),
            end=date(year, 12, 31)
        )


@dataclass(frozen=True)
class PolicyPeriod:
    """Policy coverage period."""
    start: date
    end: date

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError("Policy end date must be after start date")

    def is_active_on(self, target: date) -> bool:
        """Check if policy is active on a given date."""
        return self.start <= target <= self.end
