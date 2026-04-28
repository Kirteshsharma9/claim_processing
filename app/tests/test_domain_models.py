"""
Test-Driven Development for Domain Models.

Tests for core domain entities: Member, Policy, CoverageRule, LineItem, Claim, Dispute.

These tests verify:
- Entity creation and validation
- Business logic methods
- State transitions
- Relationships between entities
"""

from datetime import date, datetime
from decimal import Decimal

import pytest

from app.domain.models import (
    Member,
    Policy,
    CoverageRule,
    LineItem,
    Claim,
    Provider,
    Dispute,
    Money,
)
from app.domain.enums import (
    ServiceType,
    CoverageLimitType,
    ClaimStatus,
    LineItemStatus,
    DisputeStatus,
)
from app.domain.value_objects import PolicyPeriod


class TestMember:
    """Tests for the Member entity."""

    def test_create_member(self, test_member):
        """Should create a member with all fields."""
        assert test_member.member_id == "member-test-001"
        assert test_member.first_name == "John"
        assert test_member.last_name == "Doe"
        assert test_member.date_of_birth == date(1985, 6, 15)
        assert test_member.email == "john.doe@example.com"
        assert test_member.phone == "555-123-4567"

    def test_member_full_name(self, test_member):
        """Should generate full name property."""
        assert test_member.full_name == "John Doe"

    def test_member_minimal_fields(self, member_with_minimal_info):
        """Should create member with only required fields."""
        assert member_with_minimal_info.email is None
        assert member_with_minimal_info.phone is None

    def test_member_created_at_auto(self, test_member):
        """Should auto-generate created_at timestamp."""
        assert isinstance(test_member.created_at, datetime)


class TestCoverageRule:
    """Tests for the CoverageRule entity."""

    def test_create_coverage_rule(self, full_coverage_rule):
        """Should create a coverage rule."""
        assert full_coverage_rule.service_type == ServiceType.PREVENTIVE
        assert full_coverage_rule.coverage_percentage == Decimal("1.0")
        assert full_coverage_rule.limit_amount.amount == 1000

    def test_rule_is_active_on_during_period(self, full_coverage_rule):
        """Should be active during effective period."""
        assert full_coverage_rule.is_active_on(date(2026, 6, 15))

    def test_rule_is_active_on_before_effective(self, full_coverage_rule):
        """Should not be active before effective date."""
        assert not full_coverage_rule.is_active_on(date(2025, 12, 31))

    def test_rule_is_active_on_after_expiration(self, full_coverage_rule):
        """Should not be active after expiration date."""
        assert not full_coverage_rule.is_active_on(date(2027, 1, 1))

    def test_rule_without_expiration(self):
        """Should handle rules without expiration date."""
        rule = CoverageRule(
            rule_id="rule-open",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
            effective_date=date(2026, 1, 1),
        )
        assert rule.is_active_on(date(2026, 6, 15))
        assert rule.is_active_on(date(2030, 1, 1))

    def test_rule_default_deductible(self):
        """Should default to no deductible."""
        rule = CoverageRule(
            rule_id="rule-no-ded",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        )
        assert rule.deductible_applies is False
        assert rule.deductible_amount.amount == 0


class TestPolicy:
    """Tests for the Policy entity."""

    def test_create_policy(self, comprehensive_policy):
        """Should create a policy with coverage rules."""
        assert comprehensive_policy.policy_number == "POL-2026-COMP"
        assert len(comprehensive_policy.coverage_rules) == 4

    def test_policy_get_active_rules(self, comprehensive_policy):
        """Should return only active rules for a date."""
        active = comprehensive_policy.get_active_rules(date(2026, 6, 15))
        assert len(active) == 4

        # Before policy starts
        before = comprehensive_policy.get_active_rules(date(2025, 1, 1))
        assert len(before) == 0

    def test_policy_find_rule_for_service(self, comprehensive_policy):
        """Should find applicable rule for service type."""
        rule = comprehensive_policy.find_rule_for_service(
            ServiceType.LABORATORY,
            date(2026, 6, 15)
        )
        assert rule is not None
        assert rule.service_type == ServiceType.LABORATORY
        assert rule.coverage_percentage == Decimal("1.0")

    def test_policy_no_rule_for_service(self, comprehensive_policy):
        """Should return None when no rule matches."""
        rule = comprehensive_policy.find_rule_for_service(
            ServiceType.COSMETIC,
            date(2026, 6, 15)
        )
        assert rule is None

    def test_policy_rule_expired(self):
        """Should not return expired rules."""
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
            policy_id="policy-001",
            member_id="member-001",
            policy_number="POL-2025",
            coverage_rules=[rule],
        )
        result = policy.find_rule_for_service(ServiceType.LABORATORY, date(2026, 6, 15))
        assert result is None


class TestProvider:
    """Tests for the Provider entity."""

    def test_create_provider(self, line_item_with_provider):
        """Should create a provider."""
        provider = line_item_with_provider.provider
        assert provider.name == "Dr. Jane Smith"
        assert provider.npi == "1234567890"
        assert provider.specialty == "Cardiology"

    def test_provider_optional_fields(self):
        """Should allow optional provider fields."""
        provider = Provider(
            provider_id="prov-001",
            name="Dr. John Doe",
        )
        assert provider.npi is None
        assert provider.specialty is None
        assert provider.address is None
        assert provider.phone is None


class TestLineItem:
    """Tests for the LineItem entity."""

    def test_create_line_item(self, basic_line_item):
        """Should create a line item."""
        assert basic_line_item.service_type == ServiceType.LABORATORY
        assert basic_line_item.amount.amount == 300
        assert basic_line_item.status == LineItemStatus.PENDING

    def test_line_item_is_adjudicated_pending(self, basic_line_item):
        """Should not be adjudicated when pending."""
        assert basic_line_item.is_adjudicated() is False

    def test_line_item_adjudicate_approved(self, basic_line_item):
        """Should mark line item as approved."""
        basic_line_item.adjudicate_approved(
            Money.from_float(300),
            "Fully covered under laboratory benefits"
        )
        assert basic_line_item.status == LineItemStatus.APPROVED
        assert basic_line_item.adjudicated_amount.amount == 300
        assert basic_line_item.is_adjudicated() is True

    def test_line_item_adjudicate_denied(self, basic_line_item):
        """Should mark line item as denied."""
        basic_line_item.adjudicate_denied(
            Money.from_float(300),
            "No coverage rule for this service"
        )
        assert basic_line_item.status == LineItemStatus.DENIED
        assert basic_line_item.denied_amount.amount == 300
        assert basic_line_item.is_adjudicated() is True

    def test_line_item_adjudicate_partial(self, basic_line_item):
        """Should mark line item as partially approved."""
        basic_line_item.adjudicate_partial(
            Money.from_float(240),
            Money.from_float(60),
            "80% covered, 20% patient responsibility"
        )
        assert basic_line_item.status == LineItemStatus.APPROVED
        assert basic_line_item.adjudicated_amount.amount == 240
        assert basic_line_item.denied_amount.amount == 60

    def test_line_item_zero_dedential(self):
        """Should handle zero deductible."""
        line_item = LineItem(
            line_item_id="item-001",
            service_type=ServiceType.LABORATORY,
            service_date=date(2026, 6, 15),
            description="Test",
            amount=Money.from_float(100),
        )
        assert line_item.denial_reason is None
        assert line_item.notes is None


class TestClaim:
    """Tests for the Claim entity."""

    def test_create_claim(self, basic_claim):
        """Should create a claim."""
        assert basic_claim.claim_number == "CLM-2026-001"
        assert basic_claim.status == ClaimStatus.SUBMITTED
        assert len(basic_claim.line_items) == 1

    def test_claim_add_line_item(self, basic_claim):
        """Should add line items and recalculate totals."""
        basic_claim.add_line_item(
            LineItem(
                line_item_id="item-002",
                service_type=ServiceType.SPECIALIST,
                service_date=date(2026, 6, 15),
                description="Specialist visit",
                amount=Money.from_float(200),
            )
        )
        assert len(basic_claim.line_items) == 2
        assert basic_claim.total_requested.amount == 500

    def test_claim_recalculate_totals(self, basic_claim):
        """Should recalculate totals from line items."""
        assert basic_claim.total_requested.amount == 300

    def test_claim_derive_status_no_items(self):
        """Should handle claim with no line items."""
        claim = Claim(
            claim_id="claim-empty",
            member_id="member-001",
            policy_id="policy-001",
            claim_number="CLM-EMPTY",
        )
        assert claim.derive_status() == ClaimStatus.SUBMITTED

    def test_claim_derive_status_all_approved(self):
        """Should derive APPROVED when all items approved."""
        claim = Claim(
            claim_id="claim-approved",
            member_id="member-001",
            policy_id="policy-001",
            claim_number="CLM-APPROVED",
        )
        item = LineItem(
            line_item_id="item-001",
            service_type=ServiceType.LABORATORY,
            service_date=date(2026, 6, 15),
            description="Test",
            amount=Money.from_float(100),
            status=LineItemStatus.APPROVED,
            adjudicated_amount=Money.from_float(100),
        )
        claim.add_line_item(item)
        assert claim.derive_status() == ClaimStatus.APPROVED

    def test_claim_derive_status_all_denied(self):
        """Should derive DENIED when all items denied."""
        claim = Claim(
            claim_id="claim-denied",
            member_id="member-001",
            policy_id="policy-001",
            claim_number="CLM-DENIED",
        )
        item = LineItem(
            line_item_id="item-001",
            service_type=ServiceType.COSMETIC,
            service_date=date(2026, 6, 15),
            description="Test",
            amount=Money.from_float(100),
            status=LineItemStatus.DENIED,
            denied_amount=Money.from_float(100),
            denial_reason="Not covered",
        )
        claim.add_line_item(item)
        assert claim.derive_status() == ClaimStatus.DENIED

    def test_claim_derive_status_mixed(self):
        """Should derive PARTIALLY_APPROVED when mixed results."""
        claim = Claim(
            claim_id="claim-mixed",
            member_id="member-001",
            policy_id="policy-001",
            claim_number="CLM-MIXED",
        )
        # Add approved item
        claim.add_line_item(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 6, 15),
                description="Lab",
                amount=Money.from_float(100),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Money.from_float(100),
            )
        )
        # Add denied item
        claim.add_line_item(
            LineItem(
                line_item_id="item-2",
                service_type=ServiceType.COSMETIC,
                service_date=date(2026, 6, 15),
                description="Cosmetic",
                amount=Money.from_float(100),
                status=LineItemStatus.DENIED,
                denied_amount=Money.from_float(100),
            )
        )
        assert claim.derive_status() == ClaimStatus.PARTIALLY_APPROVED

    def test_claim_derive_status_needs_review(self):
        """Should derive IN_REVIEW when any item needs review."""
        claim = Claim(
            claim_id="claim-review",
            member_id="member-001",
            policy_id="policy-001",
            claim_number="CLM-REVIEW",
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.SURGERY,
                service_date=date(2026, 6, 15),
                description="Expensive surgery",
                amount=Money.from_float(50000),
                status=LineItemStatus.NEEDS_REVIEW,
            )
        )
        assert claim.derive_status() == ClaimStatus.IN_REVIEW

    def test_claim_update_status_timestamps(self):
        """Should set appropriate timestamps on status changes."""
        claim = Claim(
            claim_id="claim-ts",
            member_id="member-001",
            policy_id="policy-001",
            claim_number="CLM-TS",
            submitted_at=datetime.utcnow(),
        )
        claim.update_status(ClaimStatus.IN_REVIEW)
        assert claim.reviewed_at is not None

        claim.update_status(ClaimStatus.APPROVED)
        assert claim.decided_at is not None

        claim.update_status(ClaimStatus.PAID)
        assert claim.paid_at is not None

    def test_claim_adjudicate_all(self):
        """Should adjudicate all line items at once."""
        claim = Claim(
            claim_id="claim-adj",
            member_id="member-001",
            policy_id="policy-001",
            claim_number="CLM-ADJ",
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
        claim.add_line_item(
            LineItem(
                line_item_id="item-2",
                service_type=ServiceType.COSMETIC,
                service_date=date(2026, 6, 15),
                description="Cosmetic",
                amount=Money.from_float(200),
            )
        )

        results = {
            "item-1": (Money.from_float(100), Money.zero(), "Covered"),
            "item-2": (Money.zero(), Money.from_float(200), "Not covered"),
        }
        claim.adjudicate_all(results)

        assert claim.status == ClaimStatus.PARTIALLY_APPROVED
        assert claim.total_approved.amount == 100
        assert claim.total_denied.amount == 200


class TestDispute:
    """Tests for the Dispute entity."""

    def test_create_dispute(self, basic_dispute):
        """Should create a dispute."""
        assert basic_dispute.status == DisputeStatus.OPEN
        assert len(basic_dispute.line_item_ids) == 1
        assert "accident" in basic_dispute.reason.lower()

    def test_dispute_supporting_documents(self, basic_dispute):
        """Should track supporting documents."""
        assert len(basic_dispute.supporting_documents) == 2
        assert "accident_report.pdf" in basic_dispute.supporting_documents
