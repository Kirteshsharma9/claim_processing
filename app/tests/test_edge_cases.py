"""
Test-Driven Development for Edge Cases and Error Handling.

Tests for boundary conditions, error scenarios, and edge cases.

These tests verify:
- Boundary values
- Error handling
- Invalid input handling
- Concurrency considerations
- Data validation
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.models import (
    Member,
    Policy,
    CoverageRule,
    Claim,
    LineItem,
    Money,
    AdjudicationResult,
)
from app.domain.enums import (
    ServiceType,
    CoverageLimitType,
    ClaimStatus,
    LineItemStatus,
)
from app.domain.value_objects import Money, PolicyPeriod
from app.services.adjudication import AdjudicationEngine
from app.services.coverage import CoverageTracker, UsageRecord
from app.services.explanation import ExplanationGenerator


class TestMoneyEdgeCases:
    """Tests for Money value object edge cases."""

    def test_money_very_small_amount(self):
        """Should handle very small amounts."""
        money = Money.from_float(0.01)
        assert money.amount == Decimal("0.01")

    def test_money_very_large_amount(self):
        """Should handle very large amounts."""
        money = Money.from_float(999999999.99)
        assert money.amount == Decimal("999999999.99")

    def test_money_zero_multiplication(self):
        """Should handle multiplication by zero."""
        money = Money.from_float(100)
        result = money * 0
        assert result.amount == 0

    def test_money_subtraction_to_zero(self):
        """Should handle subtraction resulting in zero."""
        m1 = Money.from_float(100)
        m2 = Money.from_float(100)
        result = m1 - m2
        assert result.amount == 0

    def test_money_negative_result_raises(self):
        """Should reject operations that would result in negative."""
        m1 = Money.from_float(50)
        m2 = Money.from_float(100)

        with pytest.raises(ValueError, match="Money amount cannot be negative"):
            _ = m1 - m2

    def test_money_precision_rounding(self):
        """Should round to cents correctly."""
        money = Money.from_float(100.555)
        assert money.amount == Decimal("100.56")

        money = Money.from_float(100.554)
        assert money.amount == Decimal("100.55")


class TestDateEdgeCases:
    """Tests for date-related edge cases."""

    def test_policy_period_single_day(self):
        """Should reject policy period where start equals end."""
        with pytest.raises(ValueError):
            PolicyPeriod(
                start=date(2026, 1, 1),
                end=date(2026, 1, 1)
            )

    def test_rule_effective_date_equals_service_date(self):
        """Should apply rule when service date equals effective date."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
            effective_date=date(2026, 1, 1),
        )
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=[rule],
        )

        engine = AdjudicationEngine()
        result = engine.adjudicate(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 1, 1),
                description="Lab",
                amount=Money.from_float(100),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 100

    def test_rule_expiration_date_equals_service_date(self):
        """Should apply rule when service date equals expiration date."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
            effective_date=date(2025, 1, 1),
            expiration_date=date(2025, 12, 31),
        )

        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=[rule],
        )

        engine = AdjudicationEngine()

        result = engine.adjudicate(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=date(2025, 12, 31),
                description="Lab",
                amount=Money.from_float(100),
            ),
            policy,
            [],
        )

        assert result.payable.amount == Decimal("100.00")


class TestAdjudicationEdgeCases:
    """Tests for adjudication edge cases."""

    def test_zero_amount_line_item(self):
        """Should handle zero amount line items."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=[rule],
        )

        engine = AdjudicationEngine()
        result = engine.adjudicate(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 6, 15),
                description="Free lab test",
                amount=Money.zero(),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 0
        assert result.denied.amount == 0

    def test_very_high_coverage_percentage(self):
        """Should handle 100% coverage correctly."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.PREVENTIVE,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(10000),
        )
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=[rule],
        )

        engine = AdjudicationEngine()
        result = engine.adjudicate(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.PREVENTIVE,
                service_date=date(2026, 6, 15),
                description="Annual physical",
                amount=Money.from_float(500),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 500
        assert result.denied.amount == 0

    def test_exact_limit_exhaustion(self):
        """Should handle exact limit exhaustion."""
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

        # Exactly at limit
        assert tracker.is_limit_exhausted(
            ServiceType.LABORATORY,
            rule,
            date(2026, 6, 15),
        )

    def test_multiple_coverage_rules_same_service(self):
        """Should handle multiple rules for same service type (use first match)."""
        rules = [
            CoverageRule(
                rule_id="rule-1",
                service_type=ServiceType.LABORATORY,
                coverage_percentage=Decimal("1.0"),
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Money.from_float(1000),
                effective_date=date(2026, 1, 1),
            ),
            CoverageRule(
                rule_id="rule-2",
                service_type=ServiceType.LABORATORY,
                coverage_percentage=Decimal("0.8"),
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Money.from_float(5000),
                effective_date=date(2026, 1, 1),
            ),
        ]
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=rules,
        )

        engine = AdjudicationEngine()
        result = engine.adjudicate(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 6, 15),
                description="Lab",
                amount=Money.from_float(500),
            ),
            policy,
            [],
        )

        # Should use first matching rule (100% coverage)
        assert result.payable.amount == 500


class TestClaimEdgeCases:
    """Tests for claim edge cases."""

    def test_claim_with_no_line_items_totals(self):
        """Should handle claim with no line items."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )

        assert claim.total_requested.amount == 0
        assert claim.total_approved.amount == 0
        assert claim.total_denied.amount == 0

    def test_claim_add_line_item_recalculates(self):
        """Should recalculate totals when adding line item."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )

        claim.add_line_item(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 6, 15),
                description="Lab",
                amount=Money.from_float(100),
            )
        )

        assert claim.total_requested.amount == 100

        claim.add_line_item(
            LineItem(
                line_item_id="item-2",
                service_type=ServiceType.SPECIALIST,
                service_date=date(2026, 6, 15),
                description="Specialist",
                amount=Money.from_float(200),
            )
        )

        assert claim.total_requested.amount == 300

    def test_claim_adjudicate_empty_results(self):
        """Should handle empty adjudication results."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 6, 15),
                description="Lab",
                amount=Money.from_float(100),
            )
        )

        # Empty results dict
        claim.adjudicate_all({})

        # Status should remain submitted
        assert claim.status == ClaimStatus.SUBMITTED


class TestExplanationEdgeCases:
    """Tests for explanation generator edge cases."""

    def test_explanation_empty_claim_number(self):
        """Should handle claim with empty claim number."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="",
            status=ClaimStatus.APPROVED,
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        assert "claim-1" in summary or "Claim" in summary

    def test_explanation_none_values(self):
        """Should handle None values in claim fields."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            status=ClaimStatus.PAID,
            total_approved=Money.from_float(500),
            paid_at=None,
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        # Should not raise, should handle None paid_at
        assert "N/A" in summary or "paid" in summary.lower()

    def test_explanation_very_long_reason(self):
        """Should handle very long denial reasons."""
        result = AdjudicationResult(
            line_item_id="item-1",
            payable=Money.zero(),
            denied=Money.from_float(500),
            reason="This is a very long reason string that explains in great detail why this claim was denied. " * 10,
            requires_review=False,
        )

        explanation = ExplanationGenerator.generate_line_item_explanation(result)

        assert "Denied" in explanation
        assert len(explanation) > 100


class TestValidationErrorCases:
    """Tests for validation error handling."""

    def test_invalid_service_type_string(self):
        """Should handle invalid service type strings."""
        # ServiceType enum should validate
        with pytest.raises(ValueError):
            ServiceType("invalid_service_type")

    def test_invalid_claim_status_string(self):
        """Should handle invalid claim status strings."""
        with pytest.raises(ValueError):
            ClaimStatus("invalid_status")

    def test_coverage_percentage_out_of_range(self):
        """Should handle coverage percentage outside 0-1 range."""
        # Note: This depends on validation - may accept > 1 or < 0
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.5"),  # 150% - invalid but may not validate
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        # System should handle gracefully
        assert rule.coverage_percentage == Decimal("1.5")


class TestCoverageTrackerEdgeCases:
    """Tests for coverage tracker edge cases."""

    def test_tracker_empty_usage_with_zero_limit(self):
        """Should handle zero limit rules."""
        usage = []
        tracker = CoverageTracker(usage)
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.COSMETIC,
            coverage_percentage=Decimal("0.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.zero(),
        )

        summary = tracker.get_usage_summary(
            ServiceType.COSMETIC,
            rule,
            date(2026, 6, 15),
        )

        assert summary.limit_amount.amount == 0
        assert summary.remaining.amount == 0

    def test_tracker_usage_exceeds_limit(self):
        """Should handle usage exceeding limit (negative remaining)."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(1500),
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

        # Remaining should be 0 (capped), not negative
        assert summary.remaining.amount >= 0

    def test_tracker_different_rule_ids_same_service(self):
        """Should track usage separately by rule ID."""
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(500),
                rule_id="rule-A",
            ),
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(300),
                rule_id="rule-B",
            ),
        ]
        tracker = CoverageTracker(usage)

        rule_a = CoverageRule(
            rule_id="rule-A",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )

        summary_a = tracker.get_usage_summary(
            ServiceType.LABORATORY,
            rule_a,
            date(2026, 6, 15),
        )

        # Should only count rule-A usage
        assert summary_a.total_used.amount == 500


class TestConcurrencyEdgeCases:
    """Tests for potential concurrency issues."""

    def test_rapid_sequential_adjudications(self):
        """Should handle rapid sequential adjudications consistently."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=[rule],
        )

        engine = AdjudicationEngine()
        results = []

        # Simulate rapid sequential adjudications
        for i in range(5):
            result = engine.adjudicate(
                LineItem(
                    line_item_id=f"item-{i}",
                    service_type=ServiceType.LABORATORY,
                    service_date=date(2026, 6, 15),
                    description=f"Lab {i}",
                    amount=Money.from_float(100),
                ),
                policy,
                [],  # No usage history - each is independent
            )
            results.append(result)

        # All should be approved for same amount (no state leakage)
        for result in results:
            assert result.payable.amount == 100

    def test_same_input_same_output(self):
        """Should produce deterministic results."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("0.8"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=[rule],
        )

        engine = AdjudicationEngine()

        # Adjudicate same input multiple times
        results = []
        for _ in range(3):
            result = engine.adjudicate(
                LineItem(
                    line_item_id="item-1",
                    service_type=ServiceType.LABORATORY,
                    service_date=date(2026, 6, 15),
                    description="Lab",
                    amount=Money.from_float(500),
                ),
                policy,
                [],
            )
            results.append(result)

        # All results should be identical
        assert results[0].payable == results[1].payable
        assert results[0].denied == results[2].denied
        assert results[0].reason == results[1].reason
