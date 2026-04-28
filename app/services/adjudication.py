from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional

from app.domain.models import (
    LineItem,
    CoverageRule,
    Policy,
    AdjudicationResult,
    Money,
)
from app.domain.enums import ServiceType, CoverageLimitType
from app.domain.value_objects import Money
from app.services.coverage import CoverageTracker, UsageRecord


@dataclass
class AdjudicationRequest:
    """Request to adjudicate a line item."""
    line_item: LineItem
    policy: Policy
    usage_history: list[UsageRecord]


@dataclass
class AdjudicationContext:
    """Context for adjudication including all relevant data."""
    policy: Policy
    usage_history: list[UsageRecord]
    service_date: date
    other_adjudicated_items: list[LineItem]  # Other items in same claim


class AdjudicationEngine:
    """
    Core adjudication engine that applies coverage rules to line items.

    Adjudication flow:
    1. Find applicable coverage rule for the service type
    2. Check if limit is exhausted
    3. Calculate payable amount based on coverage percentage
    4. Apply deductible if applicable
    5. Generate explanation

    The engine is designed to be:
    - Deterministic: Same input always produces same output
    - Explainable: Every decision has a reason
    - Testable: Pure functions with no side effects
    """

    def __init__(self, coverage_tracker: Optional[CoverageTracker] = None):
        self.coverage_tracker = coverage_tracker

    def adjudicate(
        self,
        line_item: LineItem,
        policy: Policy,
        usage_history: list[UsageRecord]
    ) -> AdjudicationResult:
        """
        Adjudicate a single line item against policy coverage rules.

        Returns:
            AdjudicationResult with payable amount, denied amount, and reason
        """
        # Find applicable coverage rule
        rule = policy.find_rule_for_service(
            line_item.service_type,
            line_item.service_date
        )

        if rule is None:
            return AdjudicationResult(
                line_item_id=line_item.line_item_id,
                payable=Money.zero(),
                denied=line_item.amount,
                reason=f"No coverage rule found for service type: {line_item.service_type.value}",
                requires_review=False
            )

        # Initialize coverage tracker
        tracker = self.coverage_tracker or CoverageTracker(usage_history)

        # Check if limit is exhausted
        if tracker.is_limit_exhausted(
            line_item.service_type,
            rule,
            line_item.service_date
        ):
            summary = tracker.get_usage_summary(
                line_item.service_type,
                rule,
                line_item.service_date
            )
            return AdjudicationResult(
                line_item_id=line_item.line_item_id,
                payable=Money.zero(),
                denied=line_item.amount,
                reason=(
                    f"Coverage limit exhausted for {line_item.service_type.value}. "
                    f"Annual limit of ${summary.limit_amount.amount} already reached "
                    f"(used ${summary.total_used.amount})."
                ),
                requires_review=False,
                applied_rule=rule
            )

        # Calculate payable amount
        payable, denied, reason = self._calculate_payment(
            line_item=line_item,
            rule=rule,
            tracker=tracker
        )

        # Check if manual review is needed
        requires_review = self._needs_manual_review(line_item, rule, payable, denied)

        return AdjudicationResult(
            line_item_id=line_item.line_item_id,
            payable=payable,
            denied=denied,
            reason=reason,
            requires_review=requires_review,
            applied_rule=rule,
            remaining_limit=tracker.get_available_amount(
                line_item.service_type,
                rule,
                line_item.service_date
            )
        )

    def _calculate_payment(
        self,
        line_item: LineItem,
        rule: CoverageRule,
        tracker: CoverageTracker
    ) -> tuple[Money, Money, str]:
        """
        Calculate the payable and denied amounts for a line item.

        Returns:
            Tuple of (payable, denied, reason)
        """
        amount = line_item.amount
        coverage_pct = rule.coverage_percentage

        # Get remaining limit
        remaining = tracker.get_available_amount(
            line_item.service_type,
            rule,
            line_item.service_date
        )

        # Calculate base payable amount (capped by remaining limit)
        base_payable = min(amount * coverage_pct, remaining)

        # Apply deductible if applicable
        if rule.deductible_applies:
            deductible_remaining = rule.deductible_amount
            # In a real system, we'd track deductible met across all claims
            # For now, simplify: member pays deductible amount first
            deductible_portion = min(amount, deductible_remaining)
            base_payable = base_payable - (deductible_portion * (Decimal("1") - coverage_pct))

        # Ensure we don't pay more than the remaining limit
        payable = Money(min(base_payable.amount, remaining.amount))
        denied = Money(amount.amount - payable.amount)

        # Build explanation
        if denied.amount > 0 and payable.amount > 0:
            reason = (
                f"Approved {coverage_pct * 100:.0f}% of ${amount.amount} = ${payable.amount}. "
                f"Denied ${denied.amount}."
            )
            if rule.deductible_applies:
                reason += f" Deductible of ${rule.deductible_amount.amount} applies."
        elif denied.amount > 0:
            reason = (
                f"Denied: ${denied.amount}. "
                f"Service {line_item.service_type.value} not fully covered."
            )
        else:
            reason = f"Approved: 100% of ${amount.amount} covered."

        return payable, denied, reason

    def _needs_manual_review(
        self,
        line_item: LineItem,
        rule: CoverageRule,
        payable: Money,
        denied: Money
    ) -> bool:
        """
        Determine if a line item requires manual review.

        Flags for review:
        - High dollar amount (>$10,000)
        - Large denial (>$1,000)
        - Unusual service patterns
        """
        # High dollar threshold
        HIGH_DOLLAR_THRESHOLD = Decimal("10000")
        LARGE_DENIAL_THRESHOLD = Decimal("1000")

        if line_item.amount.amount >= HIGH_DOLLAR_THRESHOLD:
            return True

        if denied.amount >= LARGE_DENIAL_THRESHOLD:
            return True

        return False

    def adjudicate_claim(
        self,
        claim,
        policy: Policy,
        usage_history: list[UsageRecord]
    ) -> list[AdjudicationResult]:
        """
        Adjudicate all line items in a claim.

        Returns:
            List of AdjudicationResult for each line item
        """
        results = []
        for line_item in claim.line_items:
            result = self.adjudicate(line_item, policy, usage_history)
            results.append(result)
        return results
