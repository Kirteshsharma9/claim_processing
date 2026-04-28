"""
Test-Driven Development for Coverage Tracker.

Tests for the CoverageTracker class that tracks member usage
against coverage limits.

These tests verify:
- Usage accumulation
- Limit calculations
- Period boundaries (calendar year, per occurrence, lifetime)
- Remaining amount calculations
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.models import CoverageRule, Money
from app.domain.enums import ServiceType, CoverageLimitType
from app.services.coverage import CoverageTracker, UsageRecord, UsageSummary


class TestUsageAccumulation:
    """Tests for usage history accumulation."""

    def test_empty_usage_history(self):
        """Should handle empty usage history."""
        tracker = CoverageTracker([])
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        summary = tracker.get_usage_summary(
            ServiceType.LABORATORY,
            rule,
            date(2026, 6, 15),
        )

        assert summary.total_used.amount == 0
        assert summary.remaining.amount == 1000

    def test_single_usage_record(self):
        """Should accumulate single usage record."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(300),
                rule_id="rule-1",
            )
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        summary = tracker.get_usage_summary(
            ServiceType.LABORATORY,
            rule,
            date(2026, 6, 15),
        )

        assert summary.total_used.amount == 300
        assert summary.remaining.amount == 700

    def test_multiple_usage_records_same_service(self):
        """Should accumulate multiple records for same service."""
        usage = [
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 2, 1),
                amount_paid=Money.from_float(200),
                rule_id="rule-pt",
            ),
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(200),
                rule_id="rule-pt",
            ),
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 4, 1),
                amount_paid=Money.from_float(200),
                rule_id="rule-pt",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-pt",
            service_type=ServiceType.PHYSICAL_THERAPY,
            coverage_percentage=Decimal("0.8"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        summary = tracker.get_usage_summary(
            ServiceType.PHYSICAL_THERAPY,
            rule,
            date(2026, 6, 15),
        )

        assert summary.total_used.amount == 600
        assert summary.remaining.amount == 400

    def test_usage_records_different_services(self):
        """Should track usage separately for different services."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(300),
                rule_id="rule-lab",
            ),
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(200),
                rule_id="rule-pt",
            ),
        ]
        tracker = CoverageTracker(usage)

        lab_rule = CoverageRule(
            rule_id="rule-lab",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        pt_rule = CoverageRule(
            rule_id="rule-pt",
            service_type=ServiceType.PHYSICAL_THERAPY,
            coverage_percentage=Decimal("0.8"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(3000),
        )

        lab_summary = tracker.get_usage_summary(
            ServiceType.LABORATORY,
            lab_rule,
            date(2026, 6, 15),
        )

        pt_summary = tracker.get_usage_summary(
            ServiceType.PHYSICAL_THERAPY,
            pt_rule,
            date(2026, 6, 15),
        )

        assert lab_summary.total_used.amount == 300
        assert lab_summary.remaining.amount == 700

        assert pt_summary.total_used.amount == 200
        assert pt_summary.remaining.amount == 2800


class TestCalendarYearBoundaries:
    """Tests for calendar year limit periods."""

    def test_usage_within_same_calendar_year(self):
        """Should count usage within same calendar year."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 15),
                amount_paid=Money.from_float(500),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        summary = tracker.get_usage_summary(
            ServiceType.LABORATORY,
            rule,
            date(2026, 6, 15),
        )

        assert summary.period_start == date(2026, 1, 1)
        assert summary.period_end == date(2026, 12, 31)
        assert summary.total_used.amount == 500

    def test_usage_from_previous_year_not_counted(self):
        """Should not count usage from previous calendar year."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2025, 11, 15),
                amount_paid=Money.from_float(800),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        summary = tracker.get_usage_summary(
            ServiceType.LABORATORY,
            rule,
            date(2026, 1, 15),
        )

        assert summary.total_used.amount == 0
        assert summary.remaining.amount == 1000

    def test_usage_from_future_year_not_counted(self):
        """Should not count usage from future calendar year."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2027, 2, 15),
                amount_paid=Money.from_float(500),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        summary = tracker.get_usage_summary(
            ServiceType.LABORATORY,
            rule,
            date(2026, 6, 15),
        )

        assert summary.total_used.amount == 0

    def test_year_boundary_exact_dates(self):
        """Should handle exact year boundary dates correctly."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2025, 12, 31),
                amount_paid=Money.from_float(500),
                rule_id="rule-1",
            ),
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 1, 1),
                amount_paid=Money.from_float(300),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        # Check for 2026-06-15 (should only count 2026 usage)
        summary = tracker.get_usage_summary(
            ServiceType.LABORATORY,
            rule,
            date(2026, 6, 15),
        )
        assert summary.total_used.amount == 300

        # Check for 2025-12-31 (should only count 2025 usage)
        summary_2025 = tracker.get_usage_summary(
            ServiceType.LABORATORY,
            rule,
            date(2025, 12, 31),
        )
        assert summary_2025.total_used.amount == 500


class TestPerOccurrenceLimits:
    """Tests for per-occurrence limit types."""

    def test_per_occurrence_independent_limits(self):
        """Should treat each occurrence independently."""
        usage = [
            UsageRecord(
                service_type=ServiceType.EMERGENCY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(500),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.EMERGENCY,
            coverage_percentage=Decimal("0.9"),
            limit_type=CoverageLimitType.PER_OCCURRENCE,
            limit_amount=Money.from_float(1000),
        )

        # New occurrence should have full limit available
        summary = tracker.get_usage_summary(
            ServiceType.EMERGENCY,
            rule,
            date(2026, 6, 15),
        )

        # Per occurrence resets, so full limit is available
        assert summary.remaining.amount == 1000

    def test_per_visit_same_as_per_occurrence(self):
        """Should treat per-visit same as per-occurrence."""
        usage = [
            UsageRecord(
                service_type=ServiceType.SPECIALIST,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(100),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.SPECIALIST,
            coverage_percentage=Decimal("0.8"),
            limit_type=CoverageLimitType.PER_VISIT,
            limit_amount=Money.from_float(500),
        )

        summary = tracker.get_usage_summary(
            ServiceType.SPECIALIST,
            rule,
            date(2026, 6, 15),
        )

        assert summary.remaining.amount == 500


class TestLifetimeMaxLimits:
    """Tests for lifetime maximum limits."""

    def test_lifetime_max_accumulates_forever(self):
        """Should accumulate usage across all years for lifetime max."""
        usage = [
            UsageRecord(
                service_type=ServiceType.SURGERY,
                service_date=date(2020, 1, 1),
                amount_paid=Money.from_float(50000),
                rule_id="rule-1",
            ),
            UsageRecord(
                service_type=ServiceType.SURGERY,
                service_date=date(2022, 6, 1),
                amount_paid=Money.from_float(75000),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.SURGERY,
            coverage_percentage=Decimal("0.9"),
            limit_type=CoverageLimitType.LIFETIME_MAX,
            limit_amount=Money.from_float(250000),
        )

        summary = tracker.get_usage_summary(
            ServiceType.SURGERY,
            rule,
            date(2026, 6, 15),
        )

        assert summary.total_used.amount == 125000
        assert summary.remaining.amount == 125000
        assert summary.period_start == date(1900, 1, 1)
        assert summary.period_end is None

    def test_lifetime_max_exhausted(self):
        """Should detect exhausted lifetime max."""
        usage = [
            UsageRecord(
                service_type=ServiceType.SURGERY,
                service_date=date(2020, 1, 1),
                amount_paid=Money.from_float(250000),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.SURGERY,
            coverage_percentage=Decimal("0.9"),
            limit_type=CoverageLimitType.LIFETIME_MAX,
            limit_amount=Money.from_float(250000),
        )

        summary = tracker.get_usage_summary(
            ServiceType.SURGERY,
            rule,
            date(2026, 6, 15),
        )

        assert summary.remaining.amount == 0
        assert tracker.is_limit_exhausted(
            ServiceType.SURGERY,
            rule,
            date(2026, 6, 15),
        )


class TestLimitExhaustionChecks:
    """Tests for limit exhaustion detection."""

    def test_is_limit_exhausted_false(self):
        """Should return False when limit not exhausted."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(500),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        assert not tracker.is_limit_exhausted(
            ServiceType.LABORATORY,
            rule,
            date(2026, 6, 15),
        )

    def test_is_limit_exhausted_exactly(self):
        """Should return True when limit exactly exhausted."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(1000),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        assert tracker.is_limit_exhausted(
            ServiceType.LABORATORY,
            rule,
            date(2026, 6, 15),
        )

    def test_is_limit_exhausted_over(self):
        """Should return True when limit exceeded."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(1200),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        assert tracker.is_limit_exhausted(
            ServiceType.LABORATORY,
            rule,
            date(2026, 6, 15),
        )

    def test_get_available_amount(self):
        """Should return remaining available amount."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(400),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        available = tracker.get_available_amount(
            ServiceType.LABORATORY,
            rule,
            date(2026, 6, 15),
        )

        assert available.amount == 600


class TestUsageSummary:
    """Tests for UsageSummary value object."""

    def test_usage_summary_creation(self):
        """Should create usage summary with all fields."""
        summary = UsageSummary(
            service_type=ServiceType.LABORATORY,
            limit_type=CoverageLimitType.ANNUAL_MAX,
            total_used=Money.from_float(500),
            limit_amount=Money.from_float(1000),
            remaining=Money.from_float(500),
            period_start=date(2026, 1, 1),
            period_end=date(2026, 12, 31),
        )

        assert summary.service_type == ServiceType.LABORATORY
        assert summary.limit_type == CoverageLimitType.ANNUAL_MAX
        assert summary.total_used.amount == 500
        assert summary.limit_amount.amount == 1000
        assert summary.remaining.amount == 500

    def test_usage_summary_calculation_math(self):
        """Should correctly calculate remaining from used and limit."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(2000),
        )

        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(750),
                rule_id="rule-1",
            ),
        ]
        tracker = CoverageTracker(usage)

        summary = tracker.get_usage_summary(
            ServiceType.LABORATORY,
            rule,
            date(2026, 6, 15),
        )

        # Verify: remaining = limit - used
        assert summary.remaining.amount == summary.limit_amount.amount - summary.total_used.amount
        assert summary.remaining.amount == 1250
