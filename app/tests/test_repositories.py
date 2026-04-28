"""
Test-Driven Development for Repository Pattern.

Tests for in-memory repository implementations and Unit of Work pattern.

These tests verify:
- CRUD operations for each repository
- Unit of Work transactional behavior
- Query methods and filters
- Relationship handling
"""

from datetime import date

import pytest

from app.domain.models import (
    Member,
    Policy,
    CoverageRule,
    Claim,
    LineItem,
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
from app.repositories.in_memory import (
    UnitOfWork,
    InMemoryMemberRepository,
    InMemoryPolicyRepository,
    InMemoryClaimRepository,
    InMemoryDisputeRepository,
    InMemoryUsageRepository,
)
from app.services.coverage import UsageRecord


class TestInMemoryMemberRepository:
    """Tests for InMemoryMemberRepository."""

    def test_add_member(self):
        """Should add a new member."""
        repo = InMemoryMemberRepository()
        member = Member(
            member_id="member-1",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 6, 15),
        )

        result = repo.add(member)

        assert result.member_id == "member-1"
        assert repo.get("member-1") == member

    def test_get_member_exists(self):
        """Should return member when exists."""
        repo = InMemoryMemberRepository()
        member = Member(
            member_id="member-1",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 6, 15),
        )
        repo.add(member)

        result = repo.get("member-1")

        assert result is not None
        assert result.first_name == "John"

    def test_get_member_not_exists(self):
        """Should return None when member doesn't exist."""
        repo = InMemoryMemberRepository()

        result = repo.get("nonexistent")

        assert result is None

    def test_list_all_members(self):
        """Should list all members."""
        repo = InMemoryMemberRepository()
        repo.add(Member("m1", "John", "Doe", date(1985, 1, 1)))
        repo.add(Member("m2", "Jane", "Smith", date(1990, 1, 1)))

        result = repo.list()

        assert len(result) == 2

    def test_list_members_empty(self):
        """Should return empty list when no members."""
        repo = InMemoryMemberRepository()

        result = repo.list()

        assert len(result) == 0

    def test_update_member(self):
        """Should update existing member."""
        repo = InMemoryMemberRepository()
        member = Member(
            member_id="member-1",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 6, 15),
            email="john@example.com",
        )
        repo.add(member)

        member.email = "john.doe@example.com"
        member.phone = "555-1234"
        result = repo.update(member)

        assert result.email == "john.doe@example.com"
        assert result.phone == "555-1234"

    def test_update_member_not_exists(self):
        """Should raise when updating non-existent member."""
        repo = InMemoryMemberRepository()
        member = Member(
            member_id="member-1",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 6, 15),
        )

        with pytest.raises(ValueError, match="Member member-1 not found"):
            repo.update(member)

    def test_delete_member(self):
        """Should delete existing member."""
        repo = InMemoryMemberRepository()
        member = Member(
            member_id="member-1",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 6, 15),
        )
        repo.add(member)

        result = repo.delete("member-1")

        assert result is True
        assert repo.get("member-1") is None

    def test_delete_member_not_exists(self):
        """Should return False when deleting non-existent member."""
        repo = InMemoryMemberRepository()

        result = repo.delete("nonexistent")

        assert result is False

    def test_add_duplicate_member_raises(self):
        """Should raise when adding duplicate member."""
        repo = InMemoryMemberRepository()
        member = Member(
            member_id="member-1",
            first_name="John",
            last_name="Doe",
            date_of_birth=date(1985, 6, 15),
        )
        repo.add(member)

        with pytest.raises(ValueError, match="already exists"):
            repo.add(member)


class TestInMemoryPolicyRepository:
    """Tests for InMemoryPolicyRepository."""

    def test_add_policy(self):
        """Should add a new policy."""
        repo = InMemoryPolicyRepository()
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-001",
            period=PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31)),
        )

        result = repo.add(policy)

        assert result.policy_id == "policy-1"
        assert repo.get("policy-1") == policy

    def test_get_policy_not_exists(self):
        """Should return None when policy doesn't exist."""
        repo = InMemoryPolicyRepository()

        result = repo.get("nonexistent")

        assert result is None

    def test_get_by_member(self):
        """Should get policy by member ID."""
        repo = InMemoryPolicyRepository()
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-001",
            period=PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31)),
        )
        repo.add(policy)

        result = repo.get_by_member("member-1")

        assert result is not None
        assert result.policy_number == "POL-001"

    def test_get_by_member_not_exists(self):
        """Should return None when member has no policy."""
        repo = InMemoryPolicyRepository()

        result = repo.get_by_member("member-no-policy")

        assert result is None

    def test_list_all_policies(self):
        """Should list all policies."""
        repo = InMemoryPolicyRepository()
        repo.add(Policy("p1", "m1", "POL-001"))
        repo.add(Policy("p2", "m2", "POL-002"))

        result = repo.list()

        assert len(result) == 2

    def test_update_policy(self):
        """Should update existing policy."""
        repo = InMemoryPolicyRepository()
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-001",
            group_number="GRP-001",
        )
        repo.add(policy)

        policy.group_number = "GRP-002"
        result = repo.update(policy)

        assert result.group_number == "GRP-002"

    def test_delete_policy(self):
        """Should delete existing policy."""
        repo = InMemoryPolicyRepository()
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-001",
        )
        repo.add(policy)

        result = repo.delete("policy-1")

        assert result is True

    def test_add_duplicate_policy_raises(self):
        """Should raise when adding duplicate policy."""
        repo = InMemoryPolicyRepository()
        policy = Policy(
            policy_id="policy-1",
            member_id="member-1",
            policy_number="POL-001",
        )
        repo.add(policy)

        with pytest.raises(ValueError, match="already exists"):
            repo.add(policy)


class TestInMemoryClaimRepository:
    """Tests for InMemoryClaimRepository."""

    def test_add_claim(self):
        """Should add a new claim."""
        repo = InMemoryClaimRepository()
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )

        result = repo.add(claim)

        assert result.claim_id == "claim-1"
        assert repo.get("claim-1") == claim

    def test_get_claim_not_exists(self):
        """Should return None when claim doesn't exist."""
        repo = InMemoryClaimRepository()

        result = repo.get("nonexistent")

        assert result is None

    def test_get_by_member(self):
        """Should get claims by member ID."""
        repo = InMemoryClaimRepository()
        claim1 = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )
        claim2 = Claim(
            claim_id="claim-2",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-002",
        )
        repo.add(claim1)
        repo.add(claim2)

        result = repo.get_by_member("member-1")

        assert len(result) == 2

    def test_get_by_member_empty(self):
        """Should return empty list when member has no claims."""
        repo = InMemoryClaimRepository()

        result = repo.get_by_member("member-no-claims")

        assert len(result) == 0

    def test_get_by_claim_number(self):
        """Should get claim by claim number."""
        repo = InMemoryClaimRepository()
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )
        repo.add(claim)

        result = repo.get_by_claim_number("CLM-001")

        assert result is not None
        assert result.claim_id == "claim-1"

    def test_list_all_claims(self):
        """Should list all claims."""
        repo = InMemoryClaimRepository()
        repo.add(Claim("c1", "m1", "p1", "CLM-001"))
        repo.add(Claim("c2", "m2", "p2", "CLM-002"))

        result = repo.list()

        assert len(result) == 2

    def test_delete_claim(self):
        """Should delete existing claim."""
        repo = InMemoryClaimRepository()
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )
        repo.add(claim)

        result = repo.delete("claim-1")

        assert result is True

    def test_add_claim_with_line_items(self):
        """Should add claim with line items."""
        repo = InMemoryClaimRepository()
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
                description="Lab test",
                amount=Money.from_float(100),
            )
        )

        repo.add(claim)
        result = repo.get("claim-1")

        assert len(result.line_items) == 1

    def test_update_claim(self):
        """Should update existing claim."""
        repo = InMemoryClaimRepository()
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            status=ClaimStatus.SUBMITTED,
        )
        repo.add(claim)

        claim.update_status(ClaimStatus.APPROVED)
        result = repo.update(claim)

        assert result.status == ClaimStatus.APPROVED


class TestInMemoryDisputeRepository:
    """Tests for InMemoryDisputeRepository."""

    def test_add_dispute(self):
        """Should add a new dispute."""
        repo = InMemoryDisputeRepository()
        dispute = Dispute(
            dispute_id="dispute-1",
            claim_id="claim-1",
            member_id="member-1",
            reason="Disputed denial",
            line_item_ids=["item-1"],
        )

        result = repo.add(dispute)

        assert result.dispute_id == "dispute-1"
        assert repo.get("dispute-1") == dispute

    def test_get_by_claim(self):
        """Should get disputes by claim ID."""
        repo = InMemoryDisputeRepository()
        dispute1 = Dispute(
            dispute_id="dispute-1",
            claim_id="claim-1",
            member_id="member-1",
            reason="Dispute 1",
            line_item_ids=["item-1"],
        )
        dispute2 = Dispute(
            dispute_id="dispute-2",
            claim_id="claim-1",
            member_id="member-1",
            reason="Dispute 2",
            line_item_ids=["item-2"],
        )
        repo.add(dispute1)
        repo.add(dispute2)

        result = repo.get_by_claim("claim-1")

        assert len(result) == 2

    def test_get_by_claim_empty(self):
        """Should return empty list when claim has no disputes."""
        repo = InMemoryDisputeRepository()

        result = repo.get_by_claim("claim-no-disputes")

        assert len(result) == 0

    def test_update_dispute_status(self):
        """Should update dispute status."""
        repo = InMemoryDisputeRepository()
        dispute = Dispute(
            dispute_id="dispute-1",
            claim_id="claim-1",
            member_id="member-1",
            reason="Disputed",
            line_item_ids=["item-1"],
            status=DisputeStatus.OPEN,
        )
        repo.add(dispute)

        dispute.status = DisputeStatus.RESOLVED
        dispute.resolution_notes = "Resolved in favor of member"
        result = repo.update(dispute)

        assert result.status == DisputeStatus.RESOLVED


class TestInMemoryUsageRepository:
    """Tests for InMemoryUsageRepository."""

    def test_add_record(self):
        """Should add usage record for member."""
        repo = InMemoryUsageRepository()
        record = UsageRecord(
            service_type=ServiceType.LABORATORY,
            service_date=date(2026, 6, 15),
            amount_paid=Money.from_float(100),
            rule_id="rule-1",
        )

        repo.add_record("member-1", record)
        result = repo.get_by_member("member-1")

        assert len(result) == 1
        assert result[0].amount_paid.amount == 100

    def test_get_by_member(self):
        """Should get usage records by member ID."""
        repo = InMemoryUsageRepository()
        repo.add_record(
            "member-1",
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 3, 1),
                amount_paid=Money.from_float(100),
                rule_id="rule-1",
            ),
        )
        repo.add_record(
            "member-1",
            UsageRecord(
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 4, 1),
                amount_paid=Money.from_float(200),
                rule_id="rule-1",
            ),
        )

        result = repo.get_by_member("member-1")

        assert len(result) == 2

    def test_get_by_member_empty(self):
        """Should return empty list when member has no usage."""
        repo = InMemoryUsageRepository()

        result = repo.get_by_member("member-no-usage")

        assert len(result) == 0

    def test_update_raises(self):
        """Should raise when trying to update usage record."""
        repo = InMemoryUsageRepository()

        with pytest.raises(NotImplementedError):
            repo.update(
                UsageRecord(
                    service_type=ServiceType.LABORATORY,
                    service_date=date(2026, 6, 15),
                    amount_paid=Money.from_float(100),
                    rule_id="rule-1",
                )
            )

    def test_delete_raises(self):
        """Should raise when trying to delete usage record."""
        repo = InMemoryUsageRepository()

        with pytest.raises(NotImplementedError):
            repo.delete("some-id")


class TestUnitOfWork:
    """Tests for Unit of Work pattern."""

    def test_uow_creates_repositories(self):
        """Should create all repositories on init."""
        uow = UnitOfWork()

        assert uow.members is not None
        assert uow.policies is not None
        assert uow.claims is not None
        assert uow.disputes is not None
        assert uow.usage is not None

    def test_uow_context_manager(self):
        """Should work as context manager."""
        with UnitOfWork() as uow:
            member = Member(
                member_id="member-1",
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1985, 6, 15),
            )
            uow.members.add(member)
            result = uow.members.get("member-1")

        assert result is not None
        assert result.first_name == "John"

    def test_uow_add_member_and_policy(self):
        """Should add related entities."""
        with UnitOfWork() as uow:
            member = Member(
                member_id="member-1",
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1985, 6, 15),
            )
            policy = Policy(
                policy_id="policy-1",
                member_id="member-1",
                policy_number="POL-001",
                period=PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31)),
            )

            uow.members.add(member)
            uow.policies.add(policy)

            assert uow.members.get("member-1") is not None
            assert uow.policies.get("policy-1") is not None

    def test_uow_full_claim_workflow(self):
        """Should support full claim submission workflow."""
        with UnitOfWork() as uow:
            # Create member
            member = Member(
                member_id="member-1",
                first_name="John",
                last_name="Doe",
                date_of_birth=date(1985, 6, 15),
            )
            uow.members.add(member)

            # Create policy with coverage rule
            policy = Policy(
                policy_id="policy-1",
                member_id="member-1",
                policy_number="POL-001",
                period=PolicyPeriod(start=date(2026, 1, 1), end=date(2026, 12, 31)),
                coverage_rules=[
                    CoverageRule(
                        rule_id="rule-1",
                        service_type=ServiceType.LABORATORY,
                        coverage_percentage=1.0,
                        limit_type=CoverageLimitType.ANNUAL_MAX,
                        limit_amount=Money.from_float(1000),
                    )
                ],
            )
            uow.policies.add(policy)

            # Create claim
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
                    description="Lab test",
                    amount=Money.from_float(100),
                )
            )
            uow.claims.add(claim)

            # Verify all entities
            assert uow.members.get("member-1") is not None
            assert uow.policies.get("policy-1") is not None
            assert uow.claims.get("claim-1") is not None
            assert len(uow.claims.get("claim-1").line_items) == 1
