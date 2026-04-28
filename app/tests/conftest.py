"""
Pytest configuration and shared fixtures for TDD.

This file provides reusable fixtures that tests can use to set up
common test scenarios without duplicating code.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from app.domain.models import (
    Member,
    Policy,
    CoverageRule,
    Claim,
    LineItem,
    Provider,
    Dispute,
    Money,
    AdjudicationResult,
)
from app.domain.enums import (
    ServiceType,
    CoverageLimitType,
    ClaimStatus,
    LineItemStatus,
    DisputeStatus,
)
from app.domain.value_objects import Money, PolicyPeriod, DateRange
from app.services.adjudication import AdjudicationEngine
from app.services.coverage import CoverageTracker, UsageRecord
from app.services.explanation import ExplanationGenerator
from app.repositories.in_memory import UnitOfWork


# ============== Monetary Value Fixtures ==============


@pytest.fixture
def money_zero() -> Money:
    """Zero money value."""
    return Money.zero()


@pytest.fixture
def money_hundred() -> Money:
    """$100 money value."""
    return Money.from_float(100.0)


@pytest.fixture
def money_thousand() -> Money:
    """$1000 money value."""
    return Money.from_float(1000.0)


# ============== Date Fixtures ==============


@pytest.fixture
def today() -> date:
    """Today's date."""
    return date.today()


@pytest.fixture
def test_date() -> date:
    """Fixed test date for consistent tests."""
    return date(2026, 6, 15)


@pytest.fixture
def policy_period_2026() -> PolicyPeriod:
    """Full year 2026 policy period."""
    return PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31))


# ============== Member Fixtures ==============


@pytest.fixture
def test_member() -> Member:
    """Standard test member."""
    return Member(
        member_id="member-test-001",
        first_name="John",
        last_name="Doe",
        date_of_birth=date(1985, 6, 15),
        email="john.doe@example.com",
        phone="555-123-4567",
    )


@pytest.fixture
def member_with_minimal_info() -> Member:
    """Member with only required fields."""
    return Member(
        member_id="member-minimal-001",
        first_name="Jane",
        last_name="Smith",
        date_of_birth=date(1990, 1, 1),
    )


# ============== Coverage Rule Fixtures ==============


@pytest.fixture
def full_coverage_rule() -> CoverageRule:
    """100% coverage rule with annual limit."""
    return CoverageRule(
        rule_id="rule-full-001",
        service_type=ServiceType.PREVENTIVE,
        coverage_percentage=Decimal("1.0"),
        limit_type=CoverageLimitType.ANNUAL_MAX,
        limit_amount=Money.from_float(1000),
        effective_date=date(2026, 1, 1),
        expiration_date=date(2026, 12, 31),
    )


@pytest.fixture
def partial_coverage_rule() -> CoverageRule:
    """80% coverage rule with annual limit."""
    return CoverageRule(
        rule_id="rule-partial-001",
        service_type=ServiceType.SPECIALIST,
        coverage_percentage=Decimal("0.8"),
        limit_type=CoverageLimitType.ANNUAL_MAX,
        limit_amount=Money.from_float(5000),
        effective_date=date(2026, 1, 1),
        expiration_date=date(2026, 12, 31),
    )


@pytest.fixture
def no_coverage_rule() -> CoverageRule:
    """0% coverage rule (not covered service)."""
    return CoverageRule(
        rule_id="rule-none-001",
        service_type=ServiceType.COSMETIC,
        coverage_percentage=Decimal("0.0"),
        limit_type=CoverageLimitType.ANNUAL_MAX,
        limit_amount=Money.zero(),
        effective_date=date(2026, 1, 1),
        expiration_date=date(2026, 12, 31),
    )


@pytest.fixture
def deductible_coverage_rule() -> CoverageRule:
    """Coverage rule with deductible."""
    return CoverageRule(
        rule_id="rule-deductible-001",
        service_type=ServiceType.SURGERY,
        coverage_percentage=Decimal("0.9"),
        limit_type=CoverageLimitType.ANNUAL_MAX,
        limit_amount=Money.from_float(100000),
        deductible_applies=True,
        deductible_amount=Money.from_float(500),
        effective_date=date(2026, 1, 1),
        expiration_date=date(2026, 12, 31),
    )


# ============== Policy Fixtures ==============


@pytest.fixture
def basic_policy(test_member, policy_period_2026) -> Policy:
    """Basic policy with no coverage rules."""
    return Policy(
        policy_id="policy-basic-001",
        member_id=test_member.member_id,
        policy_number="POL-2026-BASIC",
        group_number="GRP-001",
        period=policy_period_2026,
        coverage_rules=[],
    )


@pytest.fixture
def comprehensive_policy(test_member, policy_period_2026) -> Policy:
    """Policy with multiple coverage rules for common services."""
    rules = [
        CoverageRule(
            rule_id="rule-preventive",
            service_type=ServiceType.PREVENTIVE,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(1000),
        ),
        CoverageRule(
            rule_id="rule-specialist",
            service_type=ServiceType.SPECIALIST,
            coverage_percentage=Decimal("0.8"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(5000),
        ),
        CoverageRule(
            rule_id="rule-lab",
            service_type=ServiceType.LABORATORY,
            coverage_percentage=Decimal("1.0"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(2000),
        ),
        CoverageRule(
            rule_id="rule-pt",
            service_type=ServiceType.PHYSICAL_THERAPY,
            coverage_percentage=Decimal("0.8"),
            limit_type=CoverageLimitType.ANNUAL_MAX,
            limit_amount=Money.from_float(3000),
        ),
    ]
    return Policy(
        policy_id="policy-comprehensive-001",
        member_id=test_member.member_id,
        policy_number="POL-2026-COMP",
        group_number="GRP-001",
        period=policy_period_2026,
        coverage_rules=rules,
    )


# ============== Line Item Fixtures ==============


@pytest.fixture
def basic_line_item(test_date) -> LineItem:
    """Basic line item for testing."""
    return LineItem(
        line_item_id="item-001",
        service_type=ServiceType.LABORATORY,
        service_date=test_date,
        description="Blood work panel",
        amount=Money.from_float(300),
    )


@pytest.fixture
def expensive_line_item(test_date) -> LineItem:
    """High-cost line item for testing review thresholds."""
    return LineItem(
        line_item_id="item-expensive-001",
        service_type=ServiceType.SURGERY,
        service_date=test_date,
        description="Complex surgical procedure",
        amount=Money.from_float(15000),
    )


@pytest.fixture
def line_item_with_provider(test_date) -> LineItem:
    """Line item with provider information."""
    provider = Provider(
        provider_id="provider-001",
        name="Dr. Jane Smith",
        npi="1234567890",
        specialty="Cardiology",
        address="123 Medical Center Dr",
        phone="555-987-6543",
    )
    return LineItem(
        line_item_id="item-provider-001",
        service_type=ServiceType.SPECIALIST,
        service_date=test_date,
        description="Cardiology consultation",
        amount=Money.from_float(500),
        provider=provider,
        diagnosis_codes=["I10", "I25.10"],
    )


# ============== Claim Fixtures ==============


@pytest.fixture
def basic_claim(test_member, comprehensive_policy) -> Claim:
    """Basic claim with single line item."""
    claim = Claim(
        claim_id="claim-001",
        member_id=test_member.member_id,
        policy_id=comprehensive_policy.policy_id,
        claim_number="CLM-2026-001",
        submitted_at=datetime.utcnow(),
    )
    claim.add_line_item(
        LineItem(
            line_item_id="item-001",
            service_type=ServiceType.LABORATORY,
            service_date=date(2026, 6, 15),
            description="Blood work",
            amount=Money.from_float(300),
        )
    )
    return claim


@pytest.fixture
def multi_item_claim(test_member, comprehensive_policy) -> Claim:
    """Claim with multiple line items."""
    claim = Claim(
        claim_id="claim-multi-001",
        member_id=test_member.member_id,
        policy_id=comprehensive_policy.policy_id,
        claim_number="CLM-2026-MULTI",
        submitted_at=datetime.utcnow(),
    )
    # Laboratory - covered 100%
    claim.add_line_item(
        LineItem(
            line_item_id="item-lab-001",
            service_type=ServiceType.LABORATORY,
            service_date=date(2026, 6, 15),
            description="Blood work",
            amount=Money.from_float(300),
        )
    )
    # Physical therapy - covered 80%
    claim.add_line_item(
        LineItem(
            line_item_id="item-pt-001",
            service_type=ServiceType.PHYSICAL_THERAPY,
            service_date=date(2026, 6, 15),
            description="PT session",
            amount=Money.from_float(200),
        )
    )
    # Cosmetic - not covered
    claim.add_line_item(
        LineItem(
            line_item_id="item-cosmetic-001",
            service_type=ServiceType.COSMETIC,
            service_date=date(2026, 6, 15),
            description="Cosmetic procedure",
            amount=Money.from_float(1000),
        )
    )
    return claim


@pytest.fixture
def fully_adjudicated_claim() -> Claim:
    """Claim that has been fully adjudicated with mixed results."""
    claim = Claim(
        claim_id="claim-adjudicated-001",
        member_id="member-001",
        policy_id="policy-001",
        claim_number="CLM-2026-ADJ",
        status=ClaimStatus.PARTIALLY_APPROVED,
        total_requested=Money.from_float(1500),
        total_approved=Money.from_float(540),
        total_denied=Money.from_float(960),
    )

    # Approved item
    approved_item = LineItem(
        line_item_id="item-approved-001",
        service_type=ServiceType.LABORATORY,
        service_date=date(2026, 6, 15),
        description="Blood work",
        amount=Money.from_float(300),
        status=LineItemStatus.APPROVED,
        adjudicated_amount=Money.from_float(300),
        denied_amount=Money.zero(),
    )

    # Partially approved item
    partial_item = LineItem(
        line_item_id="item-partial-001",
        service_type=ServiceType.PHYSICAL_THERAPY,
        service_date=date(2026, 6, 15),
        description="PT session",
        amount=Money.from_float(200),
        status=LineItemStatus.APPROVED,
        adjudicated_amount=Money.from_float(160),  # 80%
        denied_amount=Money.from_float(40),
    )

    # Denied item
    denied_item = LineItem(
        line_item_id="item-denied-001",
        service_type=ServiceType.COSMETIC,
        service_date=date(2026, 6, 15),
        description="Cosmetic procedure",
        amount=Money.from_float(1000),
        status=LineItemStatus.DENIED,
        adjudicated_amount=Money.zero(),
        denied_amount=Money.from_float(1000),
        denial_reason="Service not covered under policy",
    )

    claim.line_items = [approved_item, partial_item, denied_item]
    return claim


# ============== Usage Record Fixtures ==============


@pytest.fixture
def empty_usage_history() -> list[UsageRecord]:
    """Empty usage history."""
    return []


@pytest.fixture
def usage_history_with_records() -> list[UsageRecord]:
    """Usage history with some records."""
    return [
        UsageRecord(
            service_type=ServiceType.PHYSICAL_THERAPY,
            service_date=date(2026, 3, 1),
            amount_paid=Money.from_float(400),
            rule_id="rule-pt",
        ),
        UsageRecord(
            service_type=ServiceType.PHYSICAL_THERAPY,
            service_date=date(2026, 4, 1),
            amount_paid=Money.from_float(400),
            rule_id="rule-pt",
        ),
        UsageRecord(
            service_type=ServiceType.LABORATORY,
            service_date=date(2026, 5, 1),
            amount_paid=Money.from_float(200),
            rule_id="rule-lab",
        ),
    ]


@pytest.fixture
def exhausted_usage_history() -> list[UsageRecord]:
    """Usage history with exhausted limits."""
    return [
        UsageRecord(
            service_type=ServiceType.PHYSICAL_THERAPY,
            service_date=date(2026, 3, 1),
            amount_paid=Money.from_float(2500),
            rule_id="rule-pt",
        ),
    ]


# ============== Service Fixtures ==============


@pytest.fixture
def adjudication_engine() -> AdjudicationEngine:
    """Adjudication engine instance."""
    return AdjudicationEngine()


@pytest.fixture
def coverage_tracker(usage_history_with_records) -> CoverageTracker:
    """Coverage tracker with usage history."""
    return CoverageTracker(usage_history_with_records)


@pytest.fixture
def explanation_generator() -> ExplanationGenerator:
    """Explanation generator instance."""
    return ExplanationGenerator()


# ============== Repository Fixtures ==============


@pytest.fixture
def unit_of_work() -> UnitOfWork:
    """In-memory unit of work for testing."""
    return UnitOfWork()


@pytest.fixture
def populated_unit_of_work(
    test_member,
    comprehensive_policy,
    basic_claim,
) -> UnitOfWork:
    """Unit of work pre-populated with test data."""
    uow = UnitOfWork()
    uow.members.add(test_member)
    uow.policies.add(comprehensive_policy)
    uow.claims.add(basic_claim)
    return uow


# ============== Dispute Fixtures ==============


@pytest.fixture
def basic_dispute(fully_adjudicated_claim) -> Dispute:
    """Basic dispute for a claim."""
    return Dispute(
        dispute_id="dispute-001",
        claim_id=fully_adjudicated_claim.claim_id,
        member_id=fully_adjudicated_claim.member_id,
        line_item_ids=["item-denied-001"],
        reason="The cosmetic procedure was reconstructive surgery following an accident, not elective cosmetic.",
        supporting_documents=["accident_report.pdf", "physician_letter.pdf"],
    )
