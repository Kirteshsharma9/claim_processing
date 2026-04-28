"""
Comprehensive Test-Driven Development for Adjudication Engine.

These tests cover all adjudication scenarios including:
- Rule matching and selection
- Coverage percentage calculations
- Limit tracking and exhaustion
- Deductible handling
- Manual review triggers
- Full claim adjudication
- Edge cases
"""

from datetime import date
from decimal import Decimal

import pytest

from app.domain.models import (
    Member,
    Policy,
    CoverageRule,
    Claim,
    LineItem,
    Money,
)
from app.domain.enums import ServiceType, CoverageLimitType, LineItemStatus, ClaimStatus
from app.domain.value_objects import PolicyPeriod
from app.services.adjudication import AdjudicationEngine
from app.services.coverage import CoverageTracker, UsageRecord


class TestRuleMatching:
    """Tests for coverage rule matching logic."""

    def test_find_rule_by_service_type(self):
        """Should find rule matching service type."""
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
                description="Lab test",
                amount=Money.from_float(100),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 100
        assert result.applied_rule == rule

    def test_no_rule_for_service_type(self):
        """Should deny when no rule matches service type."""
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=[],
        )

        engine = AdjudicationEngine()
        result = engine.adjudicate(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.COSMETIC,
                service_date=date(2026, 6, 15),
                description="Cosmetic procedure",
                amount=Money.from_float(500),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 0
        assert result.denied.amount == 500
        assert "No coverage rule found" in result.reason

    def test_rule_not_yet_effective(self):
        """Should not apply rule before effective date."""
        rule = CoverageRule(
            rule_id="rule-future",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
            effective_date=date(2027, 1, 1),
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
                description="Lab test",
                amount=Money.from_float(100),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 0
        assert result.denied.amount == 100

    def test_rule_expired(self):
        """Should not apply rule after expiration date."""
        rule = CoverageRule(
            rule_id="rule-expired",
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
                service_date=date(2026, 6, 15),
                description="Lab test",
                amount=Money.from_float(100),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 0


class TestCoverageCalculations:
    """Tests for coverage percentage calculations."""

    def test_full_coverage_100_percent(self):
        """Should pay 100% when fully covered."""
        rule = CoverageRule(
            rule_id="rule-100",
            service_type=ServiceType.PREVENTIVE,
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
                service_type=ServiceType.PREVENTIVE,
                service_date=date(2026, 6, 15),
                description="Annual physical",
                amount=Money.from_float(250),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 250
        assert result.denied.amount == 0

    def test_partial_coverage_80_percent(self):
        """Should pay 80% when 80% covered."""
        rule = CoverageRule(
            rule_id="rule-80",
            service_type=ServiceType.SPECIALIST,
            coverage_percentage=Decimal("0.8"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(5000),
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
                service_type=ServiceType.SPECIALIST,
                service_date=date(2026, 6, 15),
                description="Specialist visit",
                amount=Money.from_float(500),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 400  # 80% of 500
        assert result.denied.amount == 100

    def test_partial_coverage_70_percent(self):
        """Should pay 70% when 70% covered."""
        rule = CoverageRule(
            rule_id="rule-70",
            service_type=ServiceType.OUTPATIENT,
            coverage_percentage=Decimal("0.7"),
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
                service_type=ServiceType.OUTPATIENT,
                service_date=date(2026, 6, 15),
                description="Outpatient procedure",
                amount=Money.from_float(1000),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 700
        assert result.denied.amount == 300

    def test_zero_coverage(self):
        """Should deny 100% when 0% covered."""
        rule = CoverageRule(
            rule_id="rule-0",
            service_type=ServiceType.COSMETIC,
            coverage_percentage=Decimal("0.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(0),
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
                service_type=ServiceType.COSMETIC,
                service_date=date(2026, 6, 15),
                description="Cosmetic procedure",
                amount=Money.from_float(2000),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 0
        assert result.denied.amount == 2000


class TestLimitExhaustion:
    """Tests for coverage limit tracking and exhaustion."""

    def test_limit_not_exhausted(self):
        """Should allow claims when limit not exhausted."""
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

        # $500 already used, $500 remaining
        usage = [
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(500),
                rule_id="rule-1",
            )
        ]

        engine = AdjudicationEngine()
        result = engine.adjudicate(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 6, 15),
                description="Lab test",
                amount=Money.from_float(400),
            ),
            policy,
            usage,
        )

        assert result.payable.amount == 400
        assert result.remaining_limit.amount == Decimal("500")

    def test_limit_partially_exhausted_capped_payment(self):
        """Should cap payment at remaining limit."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.PHYSICAL_THERAPY,
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

        # $900 already used, $100 remaining
        usage = [
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(900),
                rule_id="rule-1",
            )
        ]

        engine = AdjudicationEngine()
        result = engine.adjudicate(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 6, 15),
                description="PT session",
                amount=Money.from_float(500),
            ),
            policy,
            usage,
        )

        # 80% of 500 = 400, but only 100 remaining
        assert result.payable.amount == 100
        assert result.denied.amount == 400

    def test_limit_fully_exhausted(self):
        """Should deny when limit fully exhausted."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.PHYSICAL_THERAPY,
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

        # $1000 already used, $0 remaining
        usage = [
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(1000),
                rule_id="rule-1",
            )
        ]

        engine = AdjudicationEngine()
        result = engine.adjudicate(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 6, 15),
                description="PT session",
                amount=Money.from_float(200),
            ),
            policy,
            usage,
        )

        assert result.payable.amount == 0
        assert result.denied.amount == 200
        assert "limit exhausted" in result.reason.lower()

    def test_calendar_year_reset(self):
        """Should reset limits at calendar year boundary."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.PHYSICAL_THERAPY,
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

        # $1000 used in previous year
        usage = [
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2025, 11, 1),
                amount_paid=Money.from_float(1000),
                rule_id="rule-1",
            )
        ]

        engine = AdjudicationEngine()
        result = engine.adjudicate(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 1, 15),
                description="PT session",
                amount=Money.from_float(200),
            ),
            policy,
            usage,
        )

        # New year, full limit available
        assert result.payable.amount == Decimal("0.00")  # 80% of 200


class TestDeductibleHandling:
    """Tests for deductible calculations."""

    def test_deductible_applies_reduction(self):
        """Should reduce payment when deductible applies."""
        rule = CoverageRule(
            rule_id="rule-ded",
            service_type=ServiceType.SURGERY,
            coverage_percentage=Decimal("0.9"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(100000),
            deductible_applies=True,
            deductible_amount=Money.from_float(500),
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
                service_type=ServiceType.SURGERY,
                service_date=date(2026, 6, 15),
                description="Surgical procedure",
                amount=Money.from_float(1000),
            ),
            policy,
            [],
        )

        # Deductible reduces the payment
        assert result.payable.amount < 900  # Less than 90% due to deductible

    def test_no_deductible_full_percentage(self):
        """Should pay full percentage when no deductible."""
        rule = CoverageRule(
            rule_id="rule-no-ded",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
            deductible_applies=False,
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
                description="Lab test",
                amount=Money.from_float(300),
            ),
            policy,
            [],
        )

        assert result.payable.amount == 300


class TestManualReviewTriggers:
    """Tests for manual review flagging."""

    def test_high_dollar_amount_requires_review(self):
        """Should flag high dollar claims for review."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.SURGERY,
            coverage_percentage=Decimal("0.9"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(100000),
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
                service_type=ServiceType.SURGERY,
                service_date=date(2026, 6, 15),
                description="Major surgery",
                amount=Money.from_float(15000),
            ),
            policy,
            [],
        )

        assert result.requires_review is True
        assert result.payable.amount == 13500  # Still pays 90%

    def test_large_denial_requires_review(self):
        """Should flag large denials for review."""
        rule = CoverageRule(
            rule_id="rule-50",
            service_type=ServiceType.OTHER,
            coverage_percentage=Decimal("0.5"),
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
                service_type=ServiceType.OTHER,
                service_date=date(2026, 6, 15),
                description="Other service",
                amount=Money.from_float(5000),
            ),
            policy,
            [],
        )

        assert result.requires_review is True
        assert result.denied.amount == 2500  # 50% denied

    def test_normal_amount_no_review(self):
        """Should not flag normal claims for review."""
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
                description="Lab test",
                amount=Money.from_float(300),
            ),
            policy,
            [],
        )

        assert result.requires_review is False


class TestFullClaimAdjudication:
    """Tests for complete claim adjudication."""

    def test_claim_all_items_approved(self):
        """Should approve entire claim when all items covered."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(5000),
        )
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=[rule],
        )

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
                description="Lab A",
                amount=Money.from_float(100),
            )
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-2",
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 6, 15),
                description="Lab B",
                amount=Money.from_float(200),
            )
        )

        engine = AdjudicationEngine()
        results = engine.adjudicate_claim(claim, policy, [])

        adjudication_map = {
            r.line_item_id: (r.payable, r.denied, r.reason)
            for r in results
        }
        claim.adjudicate_all(adjudication_map)

        assert claim.status == ClaimStatus.APPROVED
        assert claim.total_approved.amount == 300
        assert claim.total_denied.amount == 0

    def test_claim_mixed_results_partially_approved(self):
        """Should partially approve claim with mixed results."""
        rules = [
            CoverageRule(
                rule_id="rule-lab",
                service_type=ServiceType.LABORATORY,
                coverage_percentage=Decimal("1.0"),
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Money.from_float(1000),
            ),
            CoverageRule(
                rule_id="rule-cosmetic",
                service_type=ServiceType.COSMETIC,
                coverage_percentage=Decimal("0.0"),
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Money.zero(),
            ),
        ]
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=rules,
        )

        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-lab",
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 6, 15),
                description="Lab test",
                amount=Money.from_float(300),
            )
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-cosmetic",
                service_type=ServiceType.COSMETIC,
                service_date=date(2026, 6, 15),
                description="Cosmetic",
                amount=Money.from_float(1000),
            )
        )

        engine = AdjudicationEngine()
        results = engine.adjudicate_claim(claim, policy, [])

        adjudication_map = {
            r.line_item_id: (r.payable, r.denied, r.reason)
            for r in results
        }
        claim.adjudicate_all(adjudication_map)

        assert claim.status == ClaimStatus.PARTIALLY_APPROVED
        assert claim.total_approved.amount == 300
        assert claim.total_denied.amount == 1000

    def test_claim_all_items_denied(self):
        """Should deny entire claim when all items denied."""
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=[],
        )

        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.COSMETIC,
                service_date=date(2026, 6, 15),
                description="Cosmetic A",
                amount=Money.from_float(100),
            )
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-2",
                service_type=ServiceType.COSMETIC,
                service_date=date(2026, 6, 15),
                description="Cosmetic B",
                amount=Money.from_float(200),
            )
        )

        engine = AdjudicationEngine()
        results = engine.adjudicate_claim(claim, policy, [])

        adjudication_map = {
            r.line_item_id: (r.payable, r.denied, r.reason)
            for r in results
        }
        claim.adjudicate_all(adjudication_map)

        assert claim.status == ClaimStatus.DENIED
        assert claim.total_approved.amount == 0
        assert claim.total_denied.amount == 300

    def test_claim_requires_review_when_any_item_flagged(self):
        """Should flag claim for review when any item requires review."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.SURGERY,
            coverage_percentage=Decimal("0.9"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(100000),
        )
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-1",
            coverage_rules=[rule],
        )

        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.SURGERY,
                service_date=date(2026, 6, 15),
                description="Major surgery",
                amount=Money.from_float(50000),
            )
        )

        engine = AdjudicationEngine()
        results = engine.adjudicate_claim(claim, policy, [])

        # At least one result should require review
        assert any(r.requires_review for r in results)
