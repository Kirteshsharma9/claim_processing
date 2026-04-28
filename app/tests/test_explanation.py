"""
Unit tests for the explanation generator.
"""

from datetime import date, datetime

from app.domain.models import Claim, LineItem, Money
from app.domain.enums import ServiceType, ClaimStatus, LineItemStatus
from app.services.explanation import ExplanationGenerator


class TestExplanationGenerator:
    """Tests for ExplanationGenerator class."""

    def test_generate_line_item_approved(self):
        """Should generate explanation for fully approved item."""
        result = type('AdjudicationResult', (), {
            'line_item_id': 'item-1',
            'payable': Money.from_float(500),
            'denied': Money.zero(),
            'reason': 'Approved: 100% covered',
            'requires_review': False,
        })()

        explanation = ExplanationGenerator.generate_line_item_explanation(result)

        assert "Approved" in explanation
        assert "$500" in explanation

    def test_generate_line_item_denied(self):
        """Should generate explanation for denied item."""
        result = type('AdjudicationResult', (), {
            'line_item_id': 'item-1',
            'payable': Money.zero(),
            'denied': Money.from_float(300),
            'reason': 'No coverage rule found',
            'requires_review': False,
        })()

        explanation = ExplanationGenerator.generate_line_item_explanation(result)

        assert "Denied" in explanation
        assert "No coverage" in explanation

    def test_generate_line_item_partial(self):
        """Should generate explanation for partially approved item."""
        result = type('AdjudicationResult', (), {
            'line_item_id': 'item-1',
            'payable': Money.from_float(400),
            'denied': Money.from_float(100),
            'reason': '80% covered',
            'requires_review': False,
        })()

        explanation = ExplanationGenerator.generate_line_item_explanation(result)

        assert "Partially approved" in explanation
        assert "$400" in explanation
        assert "$100" in explanation

    def test_generate_claim_summary_approved(self):
        """Should generate summary for approved claim."""
        claim = Claim(
            claim_id="claim-123",
            member_id="member-456",
            policy_id="policy-789",
            claim_number="CLM-2026-001",
            status=ClaimStatus.APPROVED,
            total_requested=Money.from_float(1000),
            total_approved=Money.from_float(1000),
            total_denied=Money.zero(),
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        assert "approved" in summary.lower()
        assert "CLM-2026-001" in summary
        assert "$1000" in summary

    def test_generate_claim_summary_partially_approved(self):
        """Should generate summary for partially approved claim."""
        claim = Claim(
            claim_id="claim-123",
            member_id="member-456",
            policy_id="policy-789",
            claim_number="CLM-2026-001",
            status=ClaimStatus.PARTIALLY_APPROVED,
            total_requested=Money.from_float(1000),
            total_approved=Money.from_float(600),
            total_denied=Money.from_float(400),
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        assert "partially approved" in summary.lower()
        assert "$1000" in summary
        assert "$600" in summary
        assert "$400" in summary

    def test_generate_claim_summary_denied(self):
        """Should generate summary for denied claim."""
        claim = Claim(
            claim_id="claim-123",
            member_id="member-456",
            policy_id="policy-789",
            claim_number="CLM-2026-001",
            status=ClaimStatus.DENIED,
            total_requested=Money.from_float(500),
            total_approved=Money.zero(),
            total_denied=Money.from_float(500),
        )

        summary = ExplanationGenerator.generate_claim_summary(claim)

        assert "denied" in summary.lower()
        assert "$500" in summary

    def test_generate_explanation_for_line_item(self):
        """Should generate simple explanation for a line item."""
        line_item = LineItem(
            line_item_id="item-1",
            service_type=ServiceType.LABORATORY,
            service_date=date(2026, 6, 15),
            description="Blood work",
            amount=Money.from_float(300),
            status=LineItemStatus.APPROVED,
            adjudicated_amount=Money.from_float(300),
            denied_amount=Money.zero(),
            notes="Fully covered under preventive care",
        )

        explanation = ExplanationGenerator.generate_explanation_for_line_item(line_item)

        assert "Approved" in explanation
        assert "$300" in explanation

    def test_generate_explanation_for_denied_item(self):
        """Should generate explanation for denied line item."""
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
