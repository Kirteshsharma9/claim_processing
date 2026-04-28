from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from app.domain.models import CoverageRule, Policy, Money
from app.domain.enums import CoverageLimitType, ServiceType


@dataclass
class UsageRecord:
    """Tracks member's usage of a covered service."""
    service_type: ServiceType
    service_date: date
    amount_paid: Money
    rule_id: str


@dataclass
class UsageSummary:
    """Aggregated usage for a service type within a limit period."""
    service_type: ServiceType
    limit_type: CoverageLimitType
    total_used: Money
    limit_amount: Money
    remaining: Money
    period_start: Optional[date] = None
    period_end: Optional[date] = None


class CoverageTracker:
    """
    Tracks and calculates remaining coverage limits for a member.

    Handles different limit types:
    - PER_OCCURRENCE: Reset after each claim
    - PER_VISIT: Same as per_occurrence
    - ANNUAL_MAX: Resets each calendar year
    - PER_CALENDAR_YEAR: Same as annual_max
    - LIFETIME_MAX: Never resets
    """

    def __init__(self, usage_history: list[UsageRecord]):
        self.usage_history = usage_history

    def get_usage_summary(
        self,
        service_type: ServiceType,
        rule: CoverageRule,
        service_date: date
    ) -> UsageSummary:
        """Calculate usage summary for a service type under a specific rule."""
        limit_type = rule.limit_type
        limit_amount = rule.limit_amount

        # Determine the period to sum usage over
        period_start, period_end = self._get_period_bounds(limit_type, service_date)

        # Sum usage within the period for this service type and rule
        total_used = Money.zero()
        for record in self.usage_history:
            if (record.service_type == service_type and
                record.rule_id == rule.rule_id and
                record.service_date >= period_start and
                (period_end is None or record.service_date <= period_end)):
                total_used = total_used + record.amount_paid

        remaining = Money(max(Decimal("0"), limit_amount.amount - total_used.amount))

        return UsageSummary(
            service_type=service_type,
            limit_type=limit_type,
            total_used=total_used,
            limit_amount=limit_amount,
            remaining=remaining,
            period_start=period_start,
            period_end=period_end
        )

    def _get_period_bounds(
        self,
        limit_type: CoverageLimitType,
        service_date: date
    ) -> tuple[date, Optional[date]]:
        """Get the start and end dates for a limit period."""
        if limit_type in (CoverageLimitType.PER_OCCURRENCE, CoverageLimitType.PER_VISIT):
            # No period - each occurrence is independent
            return service_date, service_date

        elif limit_type in (CoverageLimitType.ANNUAL_MAX, CoverageLimitType.PER_CALENDAR_YEAR):
            # Calendar year period
            return date(service_date.year, 1, 1), date(service_date.year, 12, 31)

        elif limit_type == CoverageLimitType.LIFETIME_MAX:
            # No end date - lifetime accumulation
            return date(1900, 1, 1), None

        # Default: treat as per_occurrence
        return service_date, service_date

    def is_limit_exhausted(
        self,
        service_type: ServiceType,
        rule: CoverageRule,
        service_date: date
    ) -> bool:
        """Check if coverage limit is fully exhausted."""
        summary = self.get_usage_summary(service_type, rule, service_date)
        return summary.remaining.amount <= 0

    def get_available_amount(
        self,
        service_type: ServiceType,
        rule: CoverageRule,
        service_date: date
    ) -> Money:
        """Get the remaining available amount under a rule."""
        summary = self.get_usage_summary(service_type, rule, service_date)
        return summary.remaining
