from datetime import date, datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field


from app.domain.models import (
    Member,
    Policy,
    CoverageRule,
    Claim,
    LineItem,
    Provider,
    Dispute,
)
from app.domain.enums import (
    ClaimStatus,
    LineItemStatus,
    ServiceType,
    CoverageLimitType,
    DisputeStatus,
)
from app.domain.value_objects import Money, PolicyPeriod
from app.services.adjudication import AdjudicationEngine, AdjudicationResult
from app.services.explanation import ExplanationGenerator
from app.repositories.sqlalchemy import DatabaseUnitOfWork
from app.services.coverage import UsageRecord


router = APIRouter()


# ============== Request/Response Models ==============


class MemberCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    email: Optional[str] = None
    phone: Optional[str] = None


class MemberResponse(BaseModel):
    member_id: str
    first_name: str
    last_name: str
    date_of_birth: date
    email: Optional[str]
    phone: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)



class CoverageRuleRequest(BaseModel):
    service_type: ServiceType
    coverage_percentage: float = Field(..., ge=0, le=1)  # 0.8 = 80%
    limit_type: CoverageLimitType
    limit_amount: float
    deductible_applies: bool = False
    deductible_amount: float = 0
    effective_date: date = Field(default_factory=date.today)
    expiration_date: Optional[date] = None


class PolicyCreateRequest(BaseModel):
    member_id: str
    policy_number: str
    group_number: Optional[str] = None
    policy_start: date
    policy_end: date
    coverage_rules: list[CoverageRuleRequest] = Field(default_factory=list)


class PolicyResponse(BaseModel):
    policy_id: str
    member_id: str
    policy_number: str
    group_number: Optional[str]
    period: Optional[Any]
    coverage_rules: list[Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)



class ProviderRequest(BaseModel):
    name: str
    npi: Optional[str] = None
    specialty: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None


class LineItemRequest(BaseModel):
    service_type: ServiceType
    service_date: date
    description: str
    amount: float
    provider: Optional[ProviderRequest] = None
    diagnosis_codes: list[str] = Field(default_factory=list)


class ClaimSubmitRequest(BaseModel):
    member_id: str
    diagnosis_codes: list[str] = Field(default_factory=list)
    accident_date: Optional[date] = None
    accident_description: Optional[str] = None
    line_items: list[LineItemRequest]


class LineItemResponse(BaseModel):
    line_item_id: str
    service_type: ServiceType
    service_date: date
    description: str
    amount: Any
    status: LineItemStatus
    adjudicated_amount: Optional[Any]
    denied_amount: Optional[Any]
    denial_reason: Optional[str]
    notes: Optional[str]
    model_config = ConfigDict(from_attributes=True)



class ClaimResponse(BaseModel):
    claim_id: str
    claim_number: str
    member_id: str
    policy_id: str
    status: ClaimStatus
    line_items: list[LineItemResponse]
    diagnosis_codes: list[str]
    total_requested: Any
    total_approved: Any
    total_denied: Any
    created_at: datetime
    submitted_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    decided_at: Optional[datetime]
    paid_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)



class AdjudicationResultResponse(BaseModel):
    line_item_id: str
    payable: float
    denied: float
    reason: str
    requires_review: bool
    remaining_limit: Optional[float]


class ClaimAdjudicationResponse(BaseModel):
    claim_id: str
    claim_number: str
    status: ClaimStatus
    results: list[AdjudicationResultResponse]
    total_requested: Any
    total_approved: Any
    total_denied: Any


class ExplanationResponse(BaseModel):
    claim_id: str
    claim_number: str
    summary: str
    line_item_explanations: list[dict]
    denial_letter: Optional[str] = None


class DisputeCreateRequest(BaseModel):
    line_item_ids: list[str]
    reason: str = Field(..., min_length=10, max_length=2000)
    supporting_documents: list[str] = Field(default_factory=list)


class DisputeResponse(BaseModel):
    dispute_id: str
    claim_id: str
    member_id: str
    line_item_ids: list[str]
    reason: str
    status: DisputeStatus
    created_at: datetime
    resolved_at: Optional[datetime]
    resolution_notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)



# ============== Member Endpoints ==============


@router.post("/members", response_model=MemberResponse, tags=["Members"])
async def create_member(request: MemberCreateRequest):
    """Create a new member."""
    member = Member(
        member_id=str(uuid4()),
        first_name=request.first_name,
        last_name=request.last_name,
        date_of_birth=request.date_of_birth,
        email=request.email,
        phone=request.phone,
    )
    with DatabaseUnitOfWork() as uow:
        return uow.members.add(member)


@router.get("/members/{member_id}", response_model=MemberResponse, tags=["Members"])
async def get_member(member_id: str):
    """Get member by ID."""
    with DatabaseUnitOfWork() as uow:
        member = uow.members.get(member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member {member_id} not found"
            )
        return member


@router.get("/members", response_model=list[MemberResponse], tags=["Members"])
async def list_members():
    """List all members."""
    with DatabaseUnitOfWork() as uow:
        return uow.members.list()


# ============== Policy Endpoints ==============


@router.post("/policies", response_model=PolicyResponse, tags=["Policies"])
async def create_policy(request: PolicyCreateRequest):
    """Create a new policy with coverage rules for a member."""
    with DatabaseUnitOfWork() as uow:
        # Verify member exists
        member = uow.members.get(request.member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member {request.member_id} not found"
            )

        # Convert coverage rules
        rules = []
        for rule_req in request.coverage_rules:
            rule = CoverageRule(
                rule_id=str(uuid4()),
                service_type=rule_req.service_type,
                coverage_percentage=rule_req.coverage_percentage,
                limit_type=rule_req.limit_type,
                limit_amount=Money.from_float(rule_req.limit_amount),
                deductible_applies=rule_req.deductible_applies,
                deductible_amount=Money.from_float(rule_req.deductible_amount),
                effective_date=rule_req.effective_date,
                expiration_date=rule_req.expiration_date,
            )
            rules.append(rule)

        policy = Policy(
            policy_id=str(uuid4()),
            member_id=request.member_id,
            policy_number=request.policy_number,
            group_number=request.group_number,
            period=PolicyPeriod(start=request.policy_start, end=request.policy_end),
            coverage_rules=rules,
        )

        return uow.policies.add(policy)


@router.get("/policies/{policy_id}", response_model=PolicyResponse, tags=["Policies"])
async def get_policy(policy_id: str):
    """Get policy by ID."""
    with DatabaseUnitOfWork() as uow:
        policy = uow.policies.get(policy_id)
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy {policy_id} not found"
            )
        return policy


@router.get(
    "/members/{member_id}/policy",
    response_model=PolicyResponse,
    tags=["Policies"]
)
async def get_member_policy(member_id: str):
    """Get the policy for a specific member."""
    with DatabaseUnitOfWork() as uow:
        policy = uow.policies.get_by_member(member_id)
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No policy found for member {member_id}"
            )
        return policy


# ============== Claim Endpoints ==============


@router.post("/claims", response_model=ClaimResponse, tags=["Claims"])
async def submit_claim(request: ClaimSubmitRequest):
    """
    Submit a new claim for adjudication.

    The claim will be automatically adjudicated against the member's policy rules.
    """
    with DatabaseUnitOfWork() as uow:
        # Verify member exists
        member = uow.members.get(request.member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member {request.member_id} not found"
            )

        # Get member's policy
        policy = uow.policies.get_by_member(request.member_id)
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No policy found for member {request.member_id}"
            )

        # Generate claim number
        claim_number = f"CLM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"

        # Create claim
        claim = Claim(
            claim_id=str(uuid4()),
            member_id=request.member_id,
            policy_id=policy.policy_id,
            claim_number=claim_number,
            diagnosis_codes=request.diagnosis_codes,
            accident_date=request.accident_date,
            accident_description=request.accident_description,
            submitted_at=datetime.utcnow(),
        )

        # Add line items
        for item_req in request.line_items:
            provider = None
            if item_req.provider:
                provider = Provider(
                    provider_id=str(uuid4()),
                    name=item_req.provider.name,
                    npi=item_req.provider.npi,
                    specialty=item_req.provider.specialty,
                    address=item_req.provider.address,
                    phone=item_req.provider.phone,
                )

            line_item = LineItem(
                line_item_id=str(uuid4()),
                service_type=item_req.service_type,
                service_date=item_req.service_date,
                description=item_req.description,
                amount=Money.from_float(item_req.amount),
                provider=provider,
                diagnosis_codes=item_req.diagnosis_codes,
            )
            claim.add_line_item(line_item)

        # Auto-adjudicate the claim
        usage_history = uow.usage.get_by_member(request.member_id)
        engine = AdjudicationEngine()
        results = engine.adjudicate_claim(claim, policy, usage_history)

        # Apply adjudication results to claim
        adjudication_map = {
            r.line_item_id: (r.payable, r.denied, r.reason)
            for r in results
        }
        claim.adjudicate_all(adjudication_map)

        # Record usage for approved amounts
        for result in results:
            if result.payable.amount > 0:
                # Find the line item to get service date
                line_item = next(
                    (li for li in claim.line_items if li.line_item_id == result.line_item_id),
                    None
                )
                if line_item:
                    usage_record = UsageRecord(
                        service_type=line_item.service_type,
                        service_date=line_item.service_date,
                        amount_paid=result.payable,
                        rule_id=result.applied_rule.rule_id if result.applied_rule else "unknown",
                    )
                    uow.usage.add_record(request.member_id, usage_record)

        # Save claim
        saved_claim = uow.claims.add(claim)

        return saved_claim

@router.get("/claims", response_model=list[ClaimResponse], tags=["Claims"])
async def list_claims():
    """List all claims."""
    with DatabaseUnitOfWork() as uow:
        claim = uow.claims.list()
        print(claim)
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claims not found"
            )
        return claim
    


@router.get("/claims/{claim_id}", response_model=ClaimResponse, tags=["Claims"])
async def get_claim(claim_id: str):
    """Get claim by ID."""
    with DatabaseUnitOfWork() as uow:
        claim = uow.claims.get(claim_id)
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim {claim_id} not found"
            )
        return claim


@router.get("/claims/{claim_id}/adjudication", response_model=ClaimAdjudicationResponse, tags=["Claims"])
async def get_claim_adjudication(claim_id: str):
    """Get detailed adjudication results for a claim."""
    with DatabaseUnitOfWork() as uow:
        claim = uow.claims.get(claim_id)
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim {claim_id} not found"
            )

        results = []
        for line_item in claim.line_items:
            result = AdjudicationResultResponse(
                line_item_id=line_item.line_item_id,
                payable=line_item.adjudicated_amount.amount if line_item.adjudicated_amount else 0,
                denied=line_item.denied_amount.amount if line_item.denied_amount else 0,
                reason=line_item.notes or "",
                requires_review=line_item.status == LineItemStatus.NEEDS_REVIEW,
                remaining_limit=None,  # Would need to track this separately
            )
            results.append(result)

        return ClaimAdjudicationResponse(
            claim_id=claim.claim_id,
            claim_number=claim.claim_number,
            status=claim.status,
            results=results,
            total_requested=claim.total_requested.amount,
            total_approved=claim.total_approved.amount,
            total_denied=claim.total_denied.amount,
        )


@router.get("/claims/{claim_id}/explanation", response_model=ExplanationResponse, tags=["Claims"])
async def get_claim_explanation(claim_id: str):
    """Get human-readable explanation of claim decision."""
    with DatabaseUnitOfWork() as uow:
        claim = uow.claims.get(claim_id)
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim {claim_id} not found"
            )

        # Get member name for denial letter
        member = uow.members.get(claim.member_id)
        member_name = member.full_name if member else "Member"

        generator = ExplanationGenerator()

        line_item_explanations = []
        for item in claim.line_items:
            line_item_explanations.append({
                "line_item_id": item.line_item_id,
                "service_type": item.service_type.value,
                "description": item.description,
                "explanation": generator.generate_explanation_for_line_item(item),
            })

        denial_letter = None
        if claim.status in (ClaimStatus.DENIED, ClaimStatus.PARTIALLY_APPROVED):
            denial_letter = generator.generate_denial_letter(claim, member_name)

        return ExplanationResponse(
            claim_id=claim.claim_id,
            claim_number=claim.claim_number,
            summary=generator.generate_claim_summary(claim),
            line_item_explanations=line_item_explanations,
            denial_letter=denial_letter,
        )


@router.get("/members/{member_id}/claims", response_model=list[ClaimResponse], tags=["Claims"])
async def list_member_claims(member_id: str):
    """List all claims for a member."""
    with DatabaseUnitOfWork() as uow:
        return uow.claims.get_by_member(member_id)


# ============== Dispute Endpoints ==============


@router.post("/claims/{claim_id}/disputes", response_model=DisputeResponse, tags=["Disputes"])
async def create_dispute(claim_id: str, request: DisputeCreateRequest):
    """Create a dispute for a claim."""
    with DatabaseUnitOfWork() as uow:
        claim = uow.claims.get(claim_id)
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim {claim_id} not found"
            )

        # Validate line items belong to this claim
        claim_line_item_ids = {li.line_item_id for li in claim.line_items}
        for line_item_id in request.line_item_ids:
            if line_item_id not in claim_line_item_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Line item {line_item_id} not found in claim {claim_id}"
                )

        dispute = Dispute(
            dispute_id=str(uuid4()),
            claim_id=claim_id,
            member_id=claim.member_id,
            line_item_ids=request.line_item_ids,
            reason=request.reason,
            supporting_documents=request.supporting_documents,
        )

        # Update claim status to appeal
        claim.update_status(ClaimStatus.APPEAL)
        uow.claims.update(claim)

        return uow.disputes.add(dispute)


@router.get("/claims/{claim_id}/disputes", response_model=list[DisputeResponse], tags=["Disputes"])
async def list_claim_disputes(claim_id: str):
    """List all disputes for a claim."""
    with DatabaseUnitOfWork() as uow:
        return uow.disputes.get_by_claim(claim_id)


@router.get("/disputes/{dispute_id}", response_model=DisputeResponse, tags=["Disputes"])
async def get_dispute(dispute_id: str):
    """Get dispute by ID."""
    with DatabaseUnitOfWork() as uow:
        dispute = uow.disputes.get(dispute_id)
        if not dispute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dispute {dispute_id} not found"
            )
        return dispute
