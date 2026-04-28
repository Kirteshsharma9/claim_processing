"""
Comprehensive Test-Driven Development for Explanation Generator.

Tests for human-readable explanation generation for claim decisions.

These tests verify:
- Line item explanations (approved, denied, partial)
- Claim summaries (all statuses)
- Denial letter generation
- Member-friendly language
"""

from datetime import date, datetime

import pytest

from app.domain.models import Claim, LineItem, Money, AdjudicationResult
from app.domain.enums import (
    ServiceType,
    ClaimStatus,
    LineItemStatus,
)
from app.services.explanation import ExplanationGenerator


class TestLineItemExplanation:
    """Tests for individual line item explanations."""

    def test_explanation_fully_approved(self):
        """Should generate explanation for fully approved item."""
        result = AdjudicationResult(
            line_item_id="item-1",
            payable=Money.from_float(500),
            denied=Money.zero(),
            reason="Approved: 100% covered under laboratory benefits",
            requires_review=False,
        )

        explanation = ExplanationGenerator.generate_line_item_explanation(result)

        assert "Approved" in explanation
        assert "$500" in explanation
        assert "100%" in explanation

    def test_explanation_fully_denied(self):
        """Should generate explanation for fully denied item."""
        result = AdjudicationResult(
            line_item_id="item-1",
            payable=Money.zero(),
            denied=Money.from_float(300),
            reason="No coverage rule found for service type: COSMETIC",
            requires_review=False,
        )

        explanation = ExplanationGenerator.generate_line_item_explanation(result)
        print(explanation)
        assert "Denied" in explanation
        assert "No coverage" in explanation

    def test_explanation_partially_approved(self):
        """Should generate explanation for partially approved item."""
        result = AdjudicationResult(
            line_item_id="item-1",
            payable=Money.from_float(400),
            denied=Money.from_float(100),
            reason="80% covered, 20% patient responsibility",
            requires_review=False,
        )

        explanation = ExplanationGenerator.generate_line_item_explanation(result)

        assert "Partially approved" in explanation
        assert "$400" in explanation
        assert "$100" in explanation

    def test_explanation_limit_exhausted(self):
        """Should generate explanation for limit exhaustion denial."""
        result = AdjudicationResult(
            line_item_id="item-1",
            payable=Money.zero(),
            denied=Money.from_float(200),
            reason="Coverage limit exhausted for PHYSICAL_THERAPY. Annual limit of $1000 already reached.",
            requires_review=False,
        )

        explanation = ExplanationGenerator.generate_line_item_explanation(result)

        assert "Denied" in explanation
        assert "limit exhausted" in explanation.lower()


class TestClaimSummary:
    """Tests for claim-level summary generation."""

    def test_summary_approved_claim(self):
        """Should generate summary for approved claim."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-2026-APPROVED",
            status=ClaimStatus.APPROVED,
            total_requested=Money.from_float(1000),
            total_approved=Money.from_float(1000),
            total_denied=Money.zero(),
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        assert "approved" in summary.lower()
        assert "CLM-2026-APPROVED" in summary
        assert "$1000" in summary

    def test_summary_denied_claim(self):
        """Should generate summary for denied claim."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-2026-DENIED",
            status=ClaimStatus.DENIED,
            total_requested=Money.from_float(500),
            total_approved=Money.zero(),
            total_denied=Money.from_float(500),
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        assert "denied" in summary.lower()
        assert "CLM-2026-DENIED" in summary
        assert "$500" in summary

    def test_summary_partially_approved_claim(self):
        """Should generate summary for partially approved claim."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-2026-PARTIAL",
            status=ClaimStatus.PARTIALLY_APPROVED,
            total_requested=Money.from_float(1500),
            total_approved=Money.from_float(600),
            total_denied=Money.from_float(900),
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        assert "partially approved" in summary.lower()
        assert "CLM-2026-PARTIAL" in summary
        assert "$1500" in summary
        assert "$600" in summary
        assert "$900" in summary

    def test_summary_in_review_claim(self):
        """Should generate summary for claim under review."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-2026-REVIEW",
            status=ClaimStatus.IN_REVIEW,
            total_requested=Money.from_float(2000),
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        assert "review" in summary.lower()
        assert "CLM-2026-REVIEW" in summary
        assert "$2000" in summary

    def test_summary_paid_claim(self):
        """Should generate summary for paid claim."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-2026-PAID",
            status=ClaimStatus.PAID,
            total_approved=Money.from_float(800),
            paid_at=datetime(2026, 7, 1),
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        assert "paid" in summary.lower()
        assert "CLM-2026-PAID" in summary
        assert "$800" in summary
        assert "2026-07-01" in summary

    def test_summary_appeal_claim(self):
        """Should generate summary for claim under appeal."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-2026-APPEAL",
            status=ClaimStatus.APPEAL,
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        assert "appeal" in summary.lower()
        assert "dispute" in summary.lower()

    def test_summary_submitted_claim(self):
        """Should generate summary for newly submitted claim."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-2026-SUBMITTED",
            status=ClaimStatus.SUBMITTED,
            total_requested=Money.from_float(500),
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        assert "CLM-2026-SUBMITTED" in summary
        assert "SUBMITTED" in summary or "status" in summary.lower()


class TestDenialLetter:
    """Tests for formal denial letter generation."""

    def test_denial_letter_structure(self, fully_adjudicated_claim):
        """Should generate properly structured denial letter."""
        member_name = "John Doe"

        letter = ExplanationGenerator.generate_denial_letter(
            fully_adjudicated_claim,
            member_name,
        )

        # Check required sections
        assert "DENIAL OF CLAIM NOTICE" in letter
        assert f"Dear {member_name}" in letter
        assert "CLAIM SUMMARY" in letter
        assert "DENIED SERVICES" in letter
        assert "APPEAL RIGHTS" in letter

    def test_denial_letter_includes_claim_details(self, fully_adjudicated_claim):
        """Should include claim number and amounts."""
        letter = ExplanationGenerator.generate_denial_letter(
            fully_adjudicated_claim,
            "John Doe",
        )

        assert fully_adjudicated_claim.claim_number in letter
        assert str(fully_adjudicated_claim.total_requested.amount) in letter
        assert str(fully_adjudicated_claim.total_denied.amount) in letter

    def test_denial_letter_includes_denied_items(self, fully_adjudicated_claim):
        """Should list denied line items with reasons."""
        letter = ExplanationGenerator.generate_denial_letter(
            fully_adjudicated_claim,
            "John Doe",
        )


        # Should include denied item details
        denied_item = fully_adjudicated_claim.line_items[2]  # The cosmetic item
        assert denied_item.service_type.value in letter
        # assert denied_item.description in letter
        assert str(denied_item.denied_amount.amount) in letter

    def test_denial_letter_includes_appeal_info(self, fully_adjudicated_claim):
        """Should include appeal rights information."""
        letter = ExplanationGenerator.generate_denial_letter(
            fully_adjudicated_claim,
            "John Doe",
        )

        assert "180 days" in letter
        assert "appeal" in letter.lower()
        assert "contact" in letter.lower()

    def test_denial_letter_no_denied_items(self):
        """Should handle claim with no denied items gracefully."""
        claim = Claim(
            claim_id="claim-1",
            member_id="member-1",
            policy_id="policy-1",
            claim_number="CLM-2026-APPROVED",
            status=ClaimStatus.APPROVED,
            total_requested=Money.from_float(500),
            total_approved=Money.from_float(500),
            total_denied=Money.zero(),
        )
        claim.add_line_item(
            LineItem(
                line_item_id="item-1",
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 6, 15),
                description="Lab test",
                amount=Money.from_float(500),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Money.from_float(500),
            )
        )

        letter = ExplanationGenerator.generate_denial_letter(claim, "John Doe")

        # Should still generate letter structure
        assert "DENIAL OF CLAIM NOTICE" in letter
        assert "DENIED SERVICES" in letter


class TestLineItemDirectExplanation:
    """Tests for direct line item explanation method."""

    def test_explanation_approved_line_item(self):
        """Should explain approved line item."""
        line_item = LineItem(
            line_item_id="item-1",
            service_type=ServiceType.LABORATORY,
            service_date=date(2026, 6, 15),
            description="Blood work",
            amount=Money.from_float(300),
            status=LineItemStatus.APPROVED,
            adjudicated_amount=Money.from_float(300),
            denied_amount=Money.zero(),
            notes="Fully covered",
        )

        explanation = ExplanationGenerator.generate_explanation_for_line_item(line_item)

        assert "Approved" in explanation
        assert "$300" in explanation

    def test_explanation_approved_with_partial_payment(self):
        """Should explain line item with partial payment."""
        line_item = LineItem(
            line_item_id="item-1",
            service_type=ServiceType.SPECIALIST,
            service_date=date(2026, 6, 15),
            description="Specialist visit",
            amount=Money.from_float(500),
            status=LineItemStatus.APPROVED,
            adjudicated_amount=Money.from_float(400),
            denied_amount=Money.from_float(100),
            notes="80% covered",
        )

        explanation = ExplanationGenerator.generate_explanation_for_line_item(line_item)

        assert "Approved" in explanation
        assert "$400" in explanation
        assert "$100" in explanation
        assert "not covered" in explanation.lower()

    def test_explanation_denied_line_item(self):
        """Should explain denied line item."""
        line_item = LineItem(
            line_item_id="item-1",
            service_type=ServiceType.COSMETIC,
            service_date=date(2026, 6, 15),
            description="Cosmetic procedure",
            amount=Money.from_float(2000),
            status=LineItemStatus.DENIED,
            adjudicated_amount=Money.zero(),
            denied_amount=Money.from_float(2000),
            denial_reason="Service not covered under policy",
        )

        explanation = ExplanationGenerator.generate_explanation_for_line_item(line_item)

        assert "Denied" in explanation
        assert "$2000" in explanation
        assert "not covered" in explanation.lower()

    def test_explanation_needs_review_line_item(self):
        """Should explain line item needing review."""
        line_item = LineItem(
            line_item_id="item-1",
            service_type=ServiceType.SURGERY,
            service_date=date(2026, 6, 15),
            description="Complex surgery",
            amount=Money.from_float(50000),
            status=LineItemStatus.NEEDS_REVIEW,
        )

        explanation = ExplanationGenerator.generate_explanation_for_line_item(line_item)

        assert "review" in explanation.lower()
        assert "manual" in explanation.lower()

    def test_explanation_pending_line_item(self):
        """Should explain pending line item."""
        line_item = LineItem(
            line_item_id="item-1",
            service_type=ServiceType.LABORATORY,
            service_date=date(2026, 6, 15),
            description="Lab test",
            amount=Money.from_float(300),
            status=LineItemStatus.PENDING,
        )

        explanation = ExplanationGenerator.generate_explanation_for_line_item(line_item)

        assert "Pending" in explanation
