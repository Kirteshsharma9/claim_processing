"""
Test-Driven Development for Value Objects.

Tests for immutable value objects: Money, DateRange, PolicyPeriod.

These tests verify:
- Immutability
- Arithmetic operations
- Validation rules
- Equality comparisons
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.value_objects import Money, DateRange, PolicyPeriod


class TestMoney:
    """Tests for the Money value object."""

    def test_create_money(self):
        """Should create money with positive amount."""
        money = Money.from_float(100.50)
        assert money.amount == 100.50

    def test_create_zero_money(self):
        """Should create zero money."""
        money = Money.zero()
        assert money.amount == 0.00

    def test_money_rounds_to_cents(self):
        """Should round to nearest cent."""
        money = Money.from_float(100.556)
        assert money.amount == Decimal("100.56")

    def test_money_negative_raises(self):
        """Should reject negative amounts."""
        with pytest.raises(ValueError, match="Money amount cannot be negative"):
            Money.from_float(-100)

    def test_money_addition(self):
        """Should add two money values."""
        m1 = Money.from_float(100)
        m2 = Money.from_float(50)
        result = m1 + m2
        assert result.amount == 150

    def test_money_subtraction(self):
        """Should subtract two money values."""
        m1 = Money.from_float(100)
        m2 = Money.from_float(30)
        result = m1 - m2
        assert result.amount == 70

    def test_money_multiplication(self):
        """Should multiply money by scalar."""
        money = Money.from_float(100)
        result = money * 0.8
        assert result.amount == 80

    def test_money_comparison_less_than(self):
        """Should compare money values."""
        m1 = Money.from_float(50)
        m2 = Money.from_float(100)
        assert m1 < m2
        assert not m2 < m1

    def test_money_comparison_greater_than(self):
        """Should compare money values."""
        m1 = Money.from_float(100)
        m2 = Money.from_float(50)
        assert m1 > m2
        assert not m2 > m1

    def test_money_equality(self):
        """Should compare money for equality."""
        m1 = Money.from_float(100)
        m2 = Money.from_float(100)
        assert m1 == m2

    def test_money_immutability(self):
        """Money should be immutable (frozen dataclass)."""
        money = Money.from_float(100)
        with pytest.raises(AttributeError):
            money.amount = 200

    def test_money_from_various_floats(self):
        """Should handle floating point precision correctly."""
        # Common floating point gotcha
        money = Money.from_float(0.1)
        assert money.amount == Decimal("0.10")

        # Another precision test
        money = Money.from_float(0.30000000000000004)
        assert money.amount == Decimal("0.30")


class TestDateRange:
    """Tests for the DateRange value object."""

    def test_create_date_range(self):
        """Should create date range with start and end."""
        start = date(2026, 1, 1)
        end = date(2026, 12, 31)
        dr = DateRange(start=start, end=end)
        assert dr.start == start
        assert dr.end == end

    def test_date_range_open_ended(self):
        """Should create open-ended date range."""
        start = date(2026, 1, 1)
        dr = DateRange(start=start)
        assert dr.start == start
        assert dr.end is None

    def test_date_range_end_before_start_raises(self):
        """Should reject end date before start date."""
        start = date(2026, 12, 31)
        end = date(2026, 1, 1)
        with pytest.raises(ValueError, match="End date cannot be before start date"):
            DateRange(start=start, end=end)

    def test_contains_within_range(self):
        """Should detect date within range."""
        dr = DateRange(start=date(2026, 1, 1), end=date(2026, 12, 31))
        assert dr.contains(date(2026, 6, 15))

    def test_contains_before_range(self):
        """Should detect date before range."""
        dr = DateRange(start=date(2026, 1, 1), end=date(2026, 12, 31))
        assert not dr.contains(date(2025, 12, 31))

    def test_contains_after_range(self):
        """Should detect date after range."""
        dr = DateRange(start=date(2026, 1, 1), end=date(2026, 12, 31))
        assert not dr.contains(date(2027, 1, 1))

    def test_contains_open_ended(self):
        """Should handle open-ended ranges."""
        dr = DateRange(start=date(2026, 1, 1))
        assert dr.contains(date(2026, 6, 15))
        assert dr.contains(date(2030, 1, 1))
        assert not dr.contains(date(2025, 12, 31))

    def test_calendar_year_factory(self):
        """Should create calendar year range."""
        dr = DateRange.calendar_year(2026)
        assert dr.start == date(2026, 1, 1)
        assert dr.end == date(2026, 12, 31)

    def test_immutability(self):
        """DateRange should be immutable."""
        dr = DateRange(start=date(2026, 1, 1), end=date(2026, 12, 31))
        with pytest.raises(AttributeError):
            dr.start = date(2027, 1, 1)


class TestPolicyPeriod:
    """Tests for the PolicyPeriod value object."""

    def test_create_policy_period(self):
        """Should create policy period."""
        period = PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31))
        assert period.start == date(2026, 1, 1)
        assert period.end == date(2026, 12, 31)

    def test_is_active_on_during_period(self):
        """Should be active during the period."""
        period = PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31))
        assert period.is_active_on(date(2026, 6, 15))

    def test_is_active_on_before_period(self):
        """Should not be active before period."""
        period = PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31))
        assert not period.is_active_on(date(2025, 12, 31))

    def test_is_active_on_after_period(self):
        """Should not be active after period."""
        period = PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31))
        assert not period.is_active_on(date(2027, 1, 1))

    def test_is_active_on_boundaries(self):
        """Should be active on boundary dates."""
        period = PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31))
        assert period.is_active_on(date(2026, 1, 1))
        assert period.is_active_on(date(2026, 12, 31))

    def test_end_before_start_raises(self):
        """Should reject end date before or equal to start date."""
        with pytest.raises(ValueError, match="end date must be after start date"):
            PolicyPeriod(start=date(2026, 12, 31), end=date(2026, 1, 1))

    def test_end_equals_start_raises(self):
        """Should reject period where end equals start."""
        with pytest.raises(ValueError, match="end date must be after start date"):
            PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 1, 1))

    def test_immutability(self):
        """PolicyPeriod should be immutable."""
        period = PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31))
        with pytest.raises(AttributeError):
            period.start = date(2027, 1, 1)
