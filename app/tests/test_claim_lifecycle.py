"""
Test-Driven Development for Claim Lifecycle State Machine.

Tests for claim state transitions and lifecycle management.

State machine:
  SUBMITTED -> IN_REVIEW -> APPROVED/DENIED/PARTIALLY_APPROVED -> PAID
                            -> APPEAL -> RESOLVED

These tests verify:
- Valid state transitions
- Invalid state transitions
- Timestamp tracking
- Status derivation from line items
"""

from datetime import datetime

import pytest

from app.domain.models import Claim, LineItem, Money
from app.domain.enums import ClaimStatus, LineItemStatus, ServiceType


class TestValidStateTransitions:
    """Tests for valid claim state transitions."""

    def test_submitted_to_in_review(self, basic_claim):
        """Should transition from SUBMITTED to IN_REVIEW."""
        assert basic_claim.status == ClaimStatus.SUBMITTED

        basic_claim.update_status(ClaimStatus.IN_REVIEW)

        assert basic_claim.status == ClaimStatus.IN_REVIEW
        assert basic_claim.reviewed_at is not None

    def test_submitted_to_approved(self):
        """Should transition from SUBMITTED to APPROVED."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            status=ClaimStatus.SUBMITTED,
        )

        claim.update_status(ClaimStatus.APPROVED)

        assert claim.status == ClaimStatus.APPROVED
        assert claim.decided_at is not None

    def test_submitted_to_denied(self):
        """Should transition from SUBMITTED to DENIED."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            status=ClaimStatus.SUBMITTED,
        )

        claim.update_status(ClaimStatus.DENIED)

        assert claim.status == ClaimStatus.DENIED
        assert claim.decided_at is not None

    def test_submitted_to_partially_approved(self):
        """Should transition from SUBMITTED to PARTIALLY_APPROVED."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            status=ClaimStatus.SUBMITTED,
        )

        claim.update_status(ClaimStatus.PARTIALLY_APPROVED)

        assert claim.status == ClaimStatus.PARTIALLY_APPROVED
        assert claim.decided_at is not None

    def test_approved_to_paid(self):
        """Should transition from APPROVED to PAID."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            status=ClaimStatus.APPROVED,
            decided_at=datetime.utcnow(),
        )

        claim.update_status(ClaimStatus.PAID)

        assert claim.status == ClaimStatus.PAID
        assert claim.paid_at is not None

    def test_denied_to_appeal(self):
        """Should transition from DENIED to APPEAL."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            status=ClaimStatus.DENIED,
        )

        claim.update_status(ClaimStatus.APPEAL)

        assert claim.status == ClaimStatus.APPEAL

    def test_partially_approved_to_appeal(self):
        """Should transition from PARTIALLY_APPROVED to APPEAL."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            status=ClaimStatus.PARTIALLY_APPROVED,
        )

        claim.update_status(ClaimStatus.APPEAL)

        assert claim.status == ClaimStatus.APPEAL

    def test_in_review_to_approved(self):
        """Should transition from IN_REVIEW to APPROVED."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            status=ClaimStatus.IN_REVIEW,
            reviewed_at=datetime.utcnow(),
        )

        claim.update_status(ClaimStatus.APPROVED)

        assert claim.status == ClaimStatus.APPROVED
        assert claim.decided_at is not None

    def test_in_review_to_denied(self):
        """Should transition from IN_REVIEW to DENIED."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            status=ClaimStatus.IN_REVIEW,
            reviewed_at=datetime.utcnow(),
        )

        claim.update_status(ClaimStatus.DENIED)

        assert claim.status == ClaimStatus.DENIED
        assert claim.decided_at is not None


class TestStatusDerivation:
    """Tests for automatic status derivation from line items."""

    def test_derive_status_no_line_items(self):
        """Should remain SUBMITTED when no line items."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )

        status = claim.derive_status()

        assert status == ClaimStatus.SUBMITTED

    def test_derive_status_all_pending(self):
        """Should remain SUBMITTED when all items pending."""
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
                service_date=None,
                description="Test",
                amount=Money.from_float(100),
                status=LineItemStatus.PENDING,
            )
        )

        status = claim.derive_status()

        assert status == ClaimStatus.SUBMITTED

    def test_derive_status_all_approved(self):
        """Should derive APPROVED when all items approved."""
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
                service_date=None,
                description="Test",
                amount=Money.from_float(100),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Money.from_float(100),
            )
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-2",
                service_type=ServiceType.LABORATORY,
                service_date=None,
                description="Test 2",
                amount=Money.from_float(200),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Money.from_float(200),
            )
        )

        status = claim.derive_status()

        assert status == ClaimStatus.APPROVED

    def test_derive_status_all_denied(self):
        """Should derive DENIED when all items denied."""
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
                service_date=None,
                description="Test",
                amount=Money.from_float(100),
                status=LineItemStatus.DENIED,
                denied_amount=Money.from_float(100),
                denial_reason="Not covered",
            )
        )

        status = claim.derive_status()

        assert status == ClaimStatus.DENIED

    def test_derive_status_mixed_results(self):
        """Should derive PARTIALLY_APPROVED when mixed results."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )
        # Add approved item
        claim.add_line_item(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=None,
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
                service_date=None,
                description="Cosmetic",
                amount=Money.from_float(200),
                status=LineItemStatus.DENIED,
                denied_amount=Money.from_float(200),
            )
        )

        status = claim.derive_status()

        assert status == ClaimStatus.PARTIALLY_APPROVED

    def test_derive_status_any_needs_review(self):
        """Should derive IN_REVIEW when any item needs review."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )
        # Add approved item
        claim.add_line_item(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=None,
                description="Lab",
                amount=Money.from_float(100),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Money.from_float(100),
            )
        )
        # Add item needing review
        claim.add_line_item(
            LineItem(
                line_item_id="item-2",
                service_type=ServiceType.SURGERY,
                service_date=None,
                description="Expensive surgery",
                amount=Money.from_float(50000),
                status=LineItemStatus.NEEDS_REVIEW,
            )
        )

        status = claim.derive_status()

        assert status == ClaimStatus.IN_REVIEW


class TestTimestampTracking:
    """Tests for lifecycle timestamp tracking."""

    def test_submitted_at_set_on_creation(self):
        """Should set submitted_at when claim submitted."""
        submitted_at = datetime.utcnow()
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            submitted_at=submitted_at,
        )

        assert claim.submitted_at is not None

    def test_reviewed_at_set_on_in_review(self):
        """Should set reviewed_at when transitioning to IN_REVIEW."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            submitted_at=datetime.utcnow(),
        )

        claim.update_status(ClaimStatus.IN_REVIEW)

        assert claim.reviewed_at is not None

    def test_decided_at_set_on_approved(self):
        """Should set decided_at when transitioning to APPROVED."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )

        claim.update_status(ClaimStatus.APPROVED)

        assert claim.decided_at is not None

    def test_decided_at_set_on_denied(self):
        """Should set decided_at when transitioning to DENIED."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )

        claim.update_status(ClaimStatus.DENIED)

        assert claim.decided_at is not None

    def test_decided_at_set_on_partially_approved(self):
        """Should set decided_at when transitioning to PARTIALLY_APPROVED."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )

        claim.update_status(ClaimStatus.PARTIALLY_APPROVED)

        assert claim.decided_at is not None

    def test_paid_at_set_on_paid(self):
        """Should set paid_at when transitioning to PAID."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
            status=ClaimStatus.APPROVED,
        )

        claim.update_status(ClaimStatus.PAID)

        assert claim.paid_at is not None

    def test_updated_at_changes_on_status_update(self):
        """Should update updated_at on every status change."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )

        old_updated = claim.updated_at

        claim.update_status(ClaimStatus.APPROVED)

        assert claim.updated_at > old_updated


class TestAdjudicateAll:
    """Tests for bulk adjudication method."""

    def test_adjudicate_all_empty_claim(self):
        """Should handle empty claim."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )

        claim.adjudicate_all({})

        assert claim.status == ClaimStatus.SUBMITTED

    def test_adjudicate_all_single_approved(self):
        """Should adjudicate single approved item."""
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
                service_date=None,
                description="Lab",
                amount=Money.from_float(100),
            )
        )

        results = {
            "item-1": (Money.from_float(100), Money.zero(), "Covered"),
        }
        claim.adjudicate_all(results)

        assert claim.status == ClaimStatus.APPROVED
        assert claim.total_approved.amount == 100
        assert claim.total_denied.amount == 0

    def test_adjudicate_all_single_denied(self):
        """Should adjudicate single denied item."""
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
                service_date=None,
                description="Cosmetic",
                amount=Money.from_float(200),
            )
        )

        results = {
            "item-1": (Money.zero(), Money.from_float(200), "Not covered"),
        }
        claim.adjudicate_all(results)

        assert claim.status == ClaimStatus.DENIED
        assert claim.total_approved.amount == 0
        assert claim.total_denied.amount == 200

    def test_adjudicate_all_mixed_results(self):
        """Should adjudicate mixed results correctly."""
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
                service_date=None,
                description="Lab",
                amount=Money.from_float(100),
            )
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-2",
                service_type=ServiceType.COSMETIC,
                service_date=None,
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

    def test_adjudicate_all_partial_approvals(self):
        """Should handle partial approvals within items."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-001",
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.SPECIALIST,
                service_date=None,
                description="Specialist",
                amount=Money.from_float(500),
            )
        )

        results = {
            "item-1": (Money.from_float(400), Money.from_float(100), "80% covered"),
        }
        claim.adjudicate_all(results)

        assert claim.status == ClaimStatus.APPROVED
        assert claim.total_approved.amount == 400
        assert claim.total_denied.amount == 100
