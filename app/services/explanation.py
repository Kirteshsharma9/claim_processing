from typing import Optional

from app.domain.models import Claim, LineItem, AdjudicationResult
from app.domain.enums import ClaimStatus, LineItemStatus


class ExplanationGenerator:
    """
    Generates human-readable explanations for claim decisions.

    Explanations are important for:
    - Member communication (denial letters, approval notices)
    - Customer service representatives
    - Audit trails and compliance
    """

    @staticmethod
    def generate_line_item_explanation(result: AdjudicationResult) -> str:
        """Generate a human-readable explanation for a line item decision."""
        if result.payable.amount == 0:
            return f"Denied: {result.reason}"

        if result.denied.amount == 0:
            return f"Approved in full: ${result.payable.amount} will be paid. {result.reason}"

        # Partial approval
        return (
            f"Partially approved: ${result.payable.amount} will be paid, "
            f"${result.denied.amount} denied. {result.reason}"
        )

    @staticmethod
    def generate_claim_summary(claim: Claim) -> str:
        """Generate a summary explanation for a claim decision."""
        status = claim.status

        if status == ClaimStatus.APPROVED:
            return (
                f"Claim {claim.claim_number} has been approved. "
                f"Total requested: ${claim.total_requested.amount}. "
                f"Total approved: ${claim.total_approved.amount}."
            )

        elif status == ClaimStatus.DENIED:
            return (
                f"Claim {claim.claim_number} has been denied. "
                f"Total requested: ${claim.total_requested.amount}. "
                f"Total approved: ${claim.total_approved.amount}."
            )

        elif status == ClaimStatus.PARTIALLY_APPROVED:
            return (
                f"Claim {claim.claim_number} has been partially approved. "
                f"Total requested: ${claim.total_requested.amount}. "
                f"Total approved: ${claim.total_approved.amount}. "
                f"Total denied: ${claim.total_denied.amount}."
            )

        elif status == ClaimStatus.IN_REVIEW:
            return (
                f"Claim {claim.claim_number} is under review. "
                f"Total requested: ${claim.total_requested.amount}."
            )

        elif status == ClaimStatus.PAID:
            return (
                f"Claim {claim.claim_number} has been paid. "
                f"Amount paid: ${claim.total_approved.amount}. "
                f"Paid date: {claim.paid_at.strftime('%Y-%m-%d') if claim.paid_at else 'N/A'}."
            )

        elif status == ClaimStatus.APPEAL:
            return (
                f"Claim {claim.claim_number} is under appeal. "
                f"A member has disputed the decision."
            )

        return f"Claim {claim.claim_number} status: {status.value}"

    @staticmethod
    def generate_denial_letter(claim: Claim, member_name: str) -> str:
        """Generate a formal denial letter for a claim."""
        denied_items = [
            item for item in claim.line_items
            if item.status == LineItemStatus.DENIED
        ]

        letter = f"""
DENIAL OF CLAIM NOTICE

Date: {claim.decided_at.strftime('%Y-%m-%d') if claim.decided_at else 'N/A'}

Dear {member_name},

We have completed our review of your claim {claim.claim_number}.

CLAIM SUMMARY
=============
Total Amount Requested: ${claim.total_requested.amount}
Total Amount Approved: ${claim.total_approved.amount}
Total Amount Denied: ${claim.total_denied.amount}

DENIED SERVICES
===============
"""

        for item in denied_items:
            letter += f"""
Service: {item.service_type.value}
Date of Service: {item.service_date}
Provider: {item.provider.name if item.provider else 'Unknown'}
Amount Requested: ${item.amount.amount}
Denial Reason: {item.denial_reason or 'Not specified'}
"""

        letter += """
APPEAL RIGHTS
=============
You have the right to appeal this decision. To file an appeal, please submit
a written request within 180 days of this notice, including any additional
documentation that supports your claim.

If you have questions about this decision, please contact our customer
service at 1-800-CLAIMS.

Sincerely,
Claims Processing Department
"""

        return letter.strip()

    @staticmethod
    def generate_explanation_for_line_item(line_item: LineItem) -> str:
        """Generate a simple explanation for a line item."""
        if line_item.status == LineItemStatus.APPROVED:
            if line_item.denied_amount and line_item.denied_amount.amount > 0:
                return (
                    f"Approved for ${line_item.adjudicated_amount.amount}. "
                    f"${line_item.denied_amount.amount} was not covered. "
                    f"{line_item.notes or ''}"
                )

            approved_amount = (
                line_item.adjudicated_amount.amount
                if line_item.adjudicated_amount
                else "0.00"
            )

            return f"Approved for ${approved_amount}. {line_item.notes or 'Fully covered.'}"

        elif line_item.status == LineItemStatus.DENIED:
            denied_amount = (
                line_item.denied_amount.amount
                if line_item.denied_amount
                else "0.00"
            )
            return f"Denied: ${denied_amount}. Reason: {line_item.denial_reason or 'Not specified'}"

        elif line_item.status == LineItemStatus.NEEDS_REVIEW:
            return "This item requires manual review. A claims specialist will evaluate."

        return "Pending adjudication."
