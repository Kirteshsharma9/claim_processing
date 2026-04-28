from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from app.domain.enums import (
    ClaimStatus,
    LineItemStatus,
    CoverageLimitType,
    ServiceType,
    DisputeStatus,
)
from app.domain.value_objects import Money, DateRange, PolicyPeriod


@dataclass
class Member:
    """Insurance policy member."""
    member_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    email: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@dataclass
class CoverageRule:
    """
    Defines coverage for a specific service type.

    Examples:
    - Physical therapy: 80% covered, up to $2000 per calendar year
    - X-ray: 100% covered, up to $500 per occurrence
    - Emergency room: 90% covered, $250 deductible applies
    """
    rule_id: str
    service_type: ServiceType
    coverage_percentage: Decimal  # 0.80 = 80% covered
    limit_type: CoverageLimitType
    limit_amount: Money
    deductible_applies: bool = False
    deductible_amount: Money = field(default_factory=Money.zero)
    effective_date: date = field(default_factory=date.today)
    expiration_date: Optional[date] = None

    def is_active_on(self, target: date) -> bool:
        """Check if rule is active on a given date."""
        if target < self.effective_date:
            return False
        if self.expiration_date and target > self.expiration_date:
            return False
        return True


@dataclass
class Policy:
    """Insurance policy containing coverage rules for a member."""
    policy_id: str
    member_id: str
    policy_number: str
    group_number: Optional[str] = None
    period: Optional[PolicyPeriod] = None
    coverage_rules: list[CoverageRule] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_active_rules(self, as_of: date) -> list[CoverageRule]:
        """Get coverage rules active on a specific date."""
        return [rule for rule in self.coverage_rules if rule.is_active_on(as_of)]

    def find_rule_for_service(
        self,
        service_type: ServiceType,
        service_date: date
    ) -> Optional[CoverageRule]:
        """Find applicable coverage rule for a service type on a given date."""
        for rule in self.coverage_rules:
            if rule.service_type == service_type and rule.is_active_on(service_date):
                return rule
        return None


@dataclass
class Provider:
    """Healthcare provider information."""
    provider_id: str
    name: str
    npi: Optional[str] = None  # National Provider Identifier
    specialty: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None


@dataclass
class LineItem:
    """
    Individual expense within a claim.

    Each line item is adjudicated independently and can have different outcomes.
    """
    line_item_id: str
    service_type: ServiceType
    service_date: date
    description: str
    amount: Money
    provider: Optional[Provider] = None
    diagnosis_codes: list[str] = field(default_factory=list)  # ICD-10 codes
    status: LineItemStatus = LineItemStatus.PENDING
    adjudicated_amount: Optional[Money] = None
    denied_amount: Optional[Money] = None
    denial_reason: Optional[str] = None
    notes: Optional[str] = None

    def is_adjudicated(self) -> bool:
        """Check if line item has been adjudicated."""
        return self.status in (
            LineItemStatus.APPROVED,
            LineItemStatus.DENIED,
            LineItemStatus.NEEDS_REVIEW
        )

    def adjudicate_approved(
        self,
        payable: Money,
        reason: Optional[str] = None
    ) -> None:
        """Mark line item as approved with payable amount."""
        self.status = LineItemStatus.APPROVED
        self.adjudicated_amount = payable
        self.denied_amount = Money.zero()
        self.denial_reason = reason
        self.notes = reason

    def adjudicate_denied(
        self,
        denied: Money,
        reason: str
    ) -> None:
        """Mark line item as denied with reason."""
        self.status = LineItemStatus.DENIED
        self.adjudicated_amount = Money.zero()
        self.denied_amount = denied
        self.denial_reason = reason
        self.notes = reason

    def adjudicate_partial(
        self,
        payable: Money,
        denied: Money,
        reason: Optional[str] = None
    ) -> None:
        """Mark line item as partially approved."""
        self.status = LineItemStatus.APPROVED  # Still considered approved if any amount paid
        self.adjudicated_amount = payable
        self.denied_amount = denied
        self.notes = reason


@dataclass
class Claim:
    """
    Insurance claim containing multiple line items.

    Claim status is derived from line item statuses:
    - All APPROVED → CLAIM APPROVED
    - All DENIED → CLAIM DENIED
    - Mixed → CLAIM PARTIALLY_APPROVED
    """
    claim_id: str
    member_id: str
    policy_id: str
    claim_number: str
    line_items: list[LineItem] = field(default_factory=list)
    diagnosis_codes: list[str] = field(default_factory=list)
    accident_date: Optional[date] = None
    accident_description: Optional[str] = None
    status: ClaimStatus = ClaimStatus.SUBMITTED
    total_requested: Money = field(default_factory=Money.zero)
    total_approved: Money = field(default_factory=Money.zero)
    total_denied: Money = field(default_factory=Money.zero)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    submitted_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    def add_line_item(self, item: LineItem) -> None:
        """Add a line item and recalculate totals."""
        self.line_items.append(item)
        self._recalculate_totals()

    def _recalculate_totals(self) -> None:
        """Recalculate total amounts from line items."""
        self.total_requested = sum(
            (item.amount for item in self.line_items),
            Money.zero()
        )
        self.total_approved = sum(
            (item.adjudicated_amount or Money.zero() for item in self.line_items),
            Money.zero()
        )
        self.total_denied = sum(
            (item.denied_amount or Money.zero() for item in self.line_items),
            Money.zero()
        )

    def derive_status(self) -> ClaimStatus:
        """Derive claim status from line item statuses."""
        if not self.line_items:
            return self.status

        adjudicated = [item for item in self.line_items if item.is_adjudicated()]
        if not adjudicated:
            return ClaimStatus.SUBMITTED

        statuses = {item.status for item in adjudicated}

        if LineItemStatus.NEEDS_REVIEW in statuses:
            return ClaimStatus.IN_REVIEW

        if len(statuses) == 1:
            if LineItemStatus.APPROVED in statuses:
                return ClaimStatus.APPROVED
            elif LineItemStatus.DENIED in statuses:
                return ClaimStatus.DENIED

        # Mixed statuses
        if LineItemStatus.APPROVED in statuses and LineItemStatus.DENIED in statuses:
            return ClaimStatus.PARTIALLY_APPROVED

        return self.status

    def update_status(self, new_status: ClaimStatus) -> None:
        """Update claim status with appropriate timestamps."""
        old_status = self.status
        self.status = new_status
        self.updated_at = datetime.utcnow()

        if new_status == ClaimStatus.IN_REVIEW and old_status == ClaimStatus.SUBMITTED:
            self.reviewed_at = datetime.utcnow()
        elif new_status in (ClaimStatus.APPROVED, ClaimStatus.DENIED, ClaimStatus.PARTIALLY_APPROVED):
            self.decided_at = datetime.utcnow()
        elif new_status == ClaimStatus.PAID:
            self.paid_at = datetime.utcnow()

    def adjudicate_all(self, results: dict[str, tuple[Money, Money, Optional[str]]]) -> None:
        """
        Adjudicate all line items at once.

        Args:
            results: Dict mapping line_item_id to (payable, denied, reason) tuple
        """
        for line_item in self.line_items:
            if line_item.line_item_id in results:
                payable, denied, reason = results[line_item.line_item_id]
                if denied.amount == 0:
                    line_item.adjudicate_approved(payable, reason)
                elif payable.amount == 0:
                    line_item.adjudicate_denied(denied, reason or "Claim denied")
                else:
                    line_item.adjudicate_partial(payable, denied, reason)

        self._recalculate_totals()
        self.update_status(self.derive_status())


@dataclass
class AdjudicationResult:
    """Result of adjudicating a single line item."""
    line_item_id: str
    payable: Money
    denied: Money
    reason: str
    requires_review: bool = False
    applied_rule: Optional[CoverageRule] = None
    remaining_limit: Optional[Money] = None


@dataclass
class Dispute:
    """Member dispute of a claim decision."""
    dispute_id: str
    claim_id: str
    member_id: str
    line_item_ids: list[str]  # Which line items are being disputed
    reason: str
    supporting_documents: list[str] = field(default_factory=list)
    status: DisputeStatus = DisputeStatus.OPEN
    created_at: datetime = field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    resolution_notes: Optional[str] = None
