"""
Unit tests for the adjudication engine.

Tests cover:
- Rule matching
- Coverage calculation
- Limit exhaustion
- Partial approvals
- Denial reasons
"""

from datetime import date
from decimal import Decimal

from app.domain.models import (
    Member,
    Policy,
    CoverageRule,
    LineItem,
    Claim,
    Money,
)
from app.domain.enums import ServiceType, CoverageLimitType, LineItemStatus
from app.domain.value_objects import Money, PolicyPeriod
from app.services.adjudication import AdjudicationEngine
from app.services.coverage import CoverageTracker, UsageRecord


class TestAdjudicationEngine:
    """Tests for the AdjudicationEngine class."""

    def create_member(self) -> Member:
        return Member(
            member_id="member-123",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 6, 15),
        )

    def create_policy_with_rules(self, rules: list[CoverageRule]) -> Policy:
        return Policy(
            policy_id="policy-456",
            member_id="member-123",
            policy_number="POL-2026-001",
            period=PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31)),
            coverage_rules=rules,
        )

    def create_line_item(
        self,
        service_type: ServiceType,
        amount: float,
        service_date: date = None,
    ) -> LineItem:
        return LineItem(
            line_item_id=f"item-{service_type.value}",
            service_type=service_type,
            service_date=service_date or date(2026, 6, 15),
            description=f"Test {service_type.value} service",
            amount=Money.from_float(amount),
        )

    def test_no_coverage_rule_found(self):
        """When no rule exists for a service type, claim should be denied."""
        policy = self.create_policy_with_rules(rules=[])
        line_item = self.create_line_item(ServiceType.PHYSICAL_THERAPY, 100.0)

        engine = AdjudicationEngine()
        result = engine.adjudicate(line_item, policy, [])

        assert result.payable.amount == 0
        assert result.denied.amount == 100
        assert "No coverage rule found" in result.reason

    def test_full_coverage(self):
        """When service is fully covered, full amount should be paid."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.PREVENTIVE,
            coverage_percentage=Decimal("1.0"),  # 100% covered
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )
        policy = self.create_policy_with_rules([rule])
        line_item = self.create_line_item(ServiceType.PREVENTIVE, 200.0)

        engine = AdjudicationEngine()
        result = engine.adjudicate(line_item, policy, [])

        assert result.payable.amount == 200
        assert result.denied.amount == 0

    def test_partial_coverage(self):
        """When service is partially covered, correct percentage should be paid."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.SPECIALIST,
            coverage_percentage=Decimal("0.8"),  # 80% covered
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(5000),
        )
        policy = self.create_policy_with_rules([rule])
        line_item = self.create_line_item(ServiceType.SPECIALIST, 500.0)

        engine = AdjudicationEngine()
        result = engine.adjudicate(line_item, policy, [])

        assert result.payable.amount == 400  # 80% of 500
        assert result.denied.amount == 100

    def test_limit_exhausted(self):
        """When annual limit is exhausted, claim should be denied."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.PHYSICAL_THERAPY,
            coverage_percentage=Decimal("0.8"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )
        policy = self.create_policy_with_rules([rule])

        # Usage history shows $1000 already used
        usage_history = [
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(1000),
                rule_id="rule-1",
            )
        ]

        line_item = self.create_line_item(ServiceType.PHYSICAL_THERAPY, 200.0)

        engine = AdjudicationEngine()
        result = engine.adjudicate(line_item, policy, usage_history)

        assert result.payable.amount == 0
        assert result.denied.amount == 200
        assert "limit exhausted" in result.reason.lower()

    def test_partial_limit_remaining(self):
        """When limit is partially used, payment should be capped by remaining."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.PHYSICAL_THERAPY,
            coverage_percentage=Decimal("0.8"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )
        policy = self.create_policy_with_rules([rule])

        # $800 already used, $200 remaining
        usage_history = [
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(800),
                rule_id="rule-1",
            )
        ]

        line_item = self.create_line_item(ServiceType.PHYSICAL_THERAPY, 500.0)
        # 80% of 500 = 400, but only 200 remaining
        # So payable should be 200

        engine = AdjudicationEngine()
        result = engine.adjudicate(line_item, policy, usage_history)

        assert result.payable.amount == 200  # Capped by remaining limit
        assert result.denied.amount == 300  # 500 - 200

    def test_high_dollar_requires_review(self):
        """High dollar claims should be flagged for manual review."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.SURGERY,
            coverage_percentage=Decimal("0.9"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(100000),
        )
        policy = self.create_policy_with_rules([rule])
        line_item = self.create_line_item(ServiceType.SURGERY, 15000.0)

        engine = AdjudicationEngine()
        result = engine.adjudicate(line_item, policy, [])

        assert result.requires_review is True
        assert result.payable.amount == 13500  # 90% of 15000

    def test_large_denial_requires_review(self):
        """Claims with large denials should be flagged for review."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.OTHER,
            coverage_percentage=Decimal("0.5"),  # Only 50% covered
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(10000),
        )
        policy = self.create_policy_with_rules([rule])
        line_item = self.create_line_item(ServiceType.OTHER, 5000.0)
        # 50% of 5000 = 2500 payable, 2500 denied (> 1000 threshold)

        engine = AdjudicationEngine()
        result = engine.adjudicate(line_item, policy, [])

        assert result.requires_review is True
        assert result.denied.amount == 2500


class TestClaimAdjudication:
    """Tests for full claim adjudication."""

    def test_claim_with_multiple_line_items(self):
        """Claim with mixed approval/denial should be partially approved."""
        # Create policy with rules
        rules = [
            CoverageRule(
                rule_id="rule-1",
                service_type=ServiceType.LABORATORY,
                coverage_percentage=Decimal("1.0"),
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Money.from_float(5000),
            ),
            CoverageRule(
                rule_id="rule-2",
                service_type=ServiceType.PHYSICAL_THERAPY,
                coverage_percentage=Decimal("0.0"),  # Not covered
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Money.from_float(0),
            ),
        ]
        policy = Policy(
            policy_id="policy-456",
            member_id="member-123",
            policy_number="POL-2026-001",
            coverage_rules=rules,
        )

        # Create claim with mixed line items
        claim = Claim(
            claim_id="claim-789",
            member_id="member-123",
            policy_id="policy-456",
            claim_number="CLM-2026-001",
        )

        # Covered item
        lab_item = LineItem(
            line_item_id="item-1",
            service_type=ServiceType.LABORATORY,
            service_date=date(2026, 6, 15),
            description="Blood work",
            amount=Money.from_float(300),
        )
        claim.add_line_item(lab_item)

        # Non-covered item
        pt_item = LineItem(
            line_item_id="item-2",
            service_type=ServiceType.PHYSICAL_THERAPY,
            service_date=date(2026, 6, 15),
            description="PT session",
            amount=Money.from_float(150),
        )
        claim.add_line_item(pt_item)

        # Adjudicate
        engine = AdjudicationEngine()
        results = engine.adjudicate_claim(claim, policy, [])

        # Apply results
        adjudication_map = {
            r.line_item_id: (r.payable, r.denied, r.reason)
            for r in results
        }
        claim.adjudicate_all(adjudication_map)

        # Verify
        assert claim.status.value == "partially_approved"
        assert claim.total_approved.amount == 300
        assert claim.total_denied.amount == 150

    def test_claim_all_approved(self):
        """Claim with all items approved should have APPROVED status."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(5000),
        )
        policy = Policy(
            policy_id="policy-456",
            member_id="member-123",
            policy_number="POL-2026-001",
            coverage_rules=[rule],
        )

        claim = Claim(
            claim_id="claim-789",
            member_id="member-123",
            policy_id="policy-456",
            claim_number="CLM-2026-001",
        )

        claim.add_line_item(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 6, 15),
                description="Blood work",
                amount=Money.from_float(300),
            )
        )

        engine = AdjudicationEngine()
        results = engine.adjudicate_claim(claim, policy, [])

        adjudication_map = {
            r.line_item_id: (r.payable, r.denied, r.reason)
            for r in results
        }
        claim.adjudicate_all(adjudication_map)

        assert claim.status == LineItemStatus.APPROVED or claim.status.value == "approved"


class TestCoverageTracker:
    """Tests for CoverageTracker class."""

    def test_usage_summary_calculation(self):
        """Usage summary should correctly calculate remaining limit."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.PHYSICAL_THERAPY,
            coverage_percentage=Decimal("0.8"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(2000),
            effective_date=date(2026, 1, 1),
            expiration_date=date(2026, 12, 31),
        )

        usage_history = [
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(500),
                rule_id="rule-1",
            ),
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 4, 1),
                amount_paid=Money.from_float(300),
                rule_id="rule-1",
            ),
        ]

        tracker = CoverageTracker(usage_history)
        summary = tracker.get_usage_summary(
            ServiceType.PHYSICAL_THERAPY,
            rule,
            date(2026, 6, 15),
        )

        assert summary.total_used.amount == 800
        assert summary.limit_amount.amount == 2000
        assert summary.remaining.amount == 1200

    def test_calendar_year_boundary(self):
        """Usage should only count within the same calendar year."""
        rule = CoverageRule(
            rule_id="rule-1",
            service_type=ServiceType.PHYSICAL_THERAPY,
            coverage_percentage=Decimal("0.8"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(2000),
        )

        # Usage from previous year
        usage_history = [
            UsageRecord(
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2025, 12, 1),
                amount_paid=Money.from_float(1500),
                rule_id="rule-1",
            ),
        ]

        tracker = CoverageTracker(usage_history)
        summary = tracker.get_usage_summary(
            ServiceType.PHYSICAL_THERAPY,
            rule,
            date(2026, 1, 15),
        )

        # Previous year usage shouldn't count
        assert summary.total_used.amount == 0
        assert summary.remaining.amount == 2000
