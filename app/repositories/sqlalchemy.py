"""
SQLAlchemy-based repository implementations for database persistence.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List
import json

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.domain.models import (
    Member,
    Policy,
    CoverageRule,
    Claim,
    LineItem,
    Provider,
    Dispute,
    Money,
)
from app.domain.enums import (
    ClaimStatus,
    LineItemStatus,
    ServiceType,
    CoverageLimitType,
    DisputeStatus,
)
from app.domain.value_objects import PolicyPeriod
from app.services.coverage import UsageRecord
from app.db.models import (
    MemberModel,
    PolicyModel,
    CoverageRuleModel,
    ClaimModel,
    LineItemModel,
    ProviderModel,
    DisputeModel,
    UsageRecordModel,
)


def _json_serialize(obj) -> Optional[str]:
    """Serialize object to JSON string."""
    if obj is None:
        return None
    if isinstance(obj, list):
        return json.dumps(obj)
    return json.dumps(obj)


def _json_deserialize(json_str: Optional[str], default=None) -> Optional[list]:
    """Deserialize JSON string to list."""
    if json_str is None:
        return default
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def _to_domain_member(model: MemberModel) -> Member:
    """Convert database model to domain entity."""
    return Member(
        member_id=model.member_id,
        first_name=model.first_name,
        last_name=model.last_name,
        date_of_birth=model.date_of_birth,
        email=model.email,
        phone=model.phone,
        created_at=model.created_at,
    )


def _to_domain_policy(model: PolicyModel) -> Policy:
    """Convert database model to domain entity."""
    rules = [
        CoverageRule(
            rule_id=r.rule_id,
            service_type=r.service_type,
            coverage_percentage=Decimal(str(r.coverage_percentage)),
            limit_type=r.limit_type,
            limit_amount=Money(Decimal(str(r.limit_amount))),
            deductible_applies=r.deductible_applies,
            deductible_amount=Money(Decimal(str(r.deductible_amount))),
            effective_date=r.effective_date,
            expiration_date=r.expiration_date,
        )
        for r in model.coverage_rules
    ]
    return Policy(
        policy_id=model.policy_id,
        member_id=model.member_id,
        policy_number=model.policy_number,
        group_number=model.group_number,
        period=PolicyPeriod(start=model.policy_start, end=model.policy_end),
        coverage_rules=rules,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _to_domain_provider(model: ProviderModel) -> Optional[Provider]:
    """Convert database model to domain entity."""
    if model is None:
        return None
    return Provider(
        provider_id=model.provider_id,
        name=model.name,
        npi=model.npi,
        specialty=model.specialty,
        address=model.address,
        phone=model.phone,
    )


def _to_domain_line_item(model: LineItemModel) -> LineItem:
    """Convert database model to domain entity."""
    return LineItem(
        line_item_id=model.line_item_id,
        service_type=model.service_type,
        service_date=model.service_date,
        description=model.description,
        amount=Money(Decimal(str(model.amount))),
        provider=_to_domain_provider(model.provider) if model.provider else None,
        diagnosis_codes=_json_deserialize(model.diagnosis_codes, []) or [],
        status=model.status,
        adjudicated_amount=Money(Decimal(str(model.adjudicated_amount))) if model.adjudicated_amount else None,
        denied_amount=Money(Decimal(str(model.denied_amount))) if model.denied_amount else None,
        denial_reason=model.denial_reason,
        notes=model.notes,
    )


def _to_domain_claim(model: ClaimModel) -> Claim:
    """Convert database model to domain entity."""
    line_items = [_to_domain_line_item(li) for li in model.line_items]
    return Claim(
        claim_id=model.claim_id,
        member_id=model.member_id,
        policy_id=model.policy_id,
        claim_number=model.claim_number,
        line_items=line_items,
        diagnosis_codes=_json_deserialize(model.diagnosis_codes, []) or [],
        accident_date=model.accident_date,
        accident_description=model.accident_description,
        status=model.status,
        total_requested=Money(Decimal(str(model.total_requested))),
        total_approved=Money(Decimal(str(model.total_approved))),
        total_denied=Money(Decimal(str(model.total_denied))),
        created_at=model.created_at,
        updated_at=model.created_at,  # Use created_at as updated_at for now
        submitted_at=model.submitted_at,
        reviewed_at=model.reviewed_at,
        decided_at=model.decided_at,
        paid_at=model.paid_at,
    )


def _to_domain_dispute(model: DisputeModel) -> Dispute:
    """Convert database model to domain entity."""
    return Dispute(
        dispute_id=model.dispute_id,
        claim_id=model.claim_id,
        member_id=model.member_id,
        line_item_ids=_json_deserialize(model.line_item_ids, []) or [],
        reason=model.reason,
        supporting_documents=_json_deserialize(model.supporting_documents, []) or [],
        status=model.status,
        created_at=model.created_at,
        reviewed_at=model.reviewed_at,
        resolved_at=model.resolved_at,
        resolution_notes=model.resolution_notes,
    )


def _to_domain_usage_record(model: UsageRecordModel) -> UsageRecord:
    """Convert database model to domain entity."""
    return UsageRecord(
        service_type=model.service_type,
        service_date=model.service_date,
        amount_paid=Money(Decimal(str(model.amount_paid))),
        rule_id=model.rule_id,
    )


class DatabaseMemberRepository:
    """SQLAlchemy implementation of member repository."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, id: str) -> Optional[Member]:
        model = self.session.get(MemberModel, id)
        return _to_domain_member(model) if model else None

    def list(self, **filters) -> List[Member]:
        query = select(MemberModel)
        members = self.session.execute(query).scalars().all()
        return [_to_domain_member(m) for m in members]

    def add(self, entity: Member) -> Member:
        model = MemberModel(
            member_id=entity.member_id,
            first_name=entity.first_name,
            last_name=entity.last_name,
            date_of_birth=entity.date_of_birth,
            email=entity.email,
            phone=entity.phone,
            created_at=entity.created_at,
        )
        self.session.add(model)
        self.session.commit()
        return entity

    def update(self, entity: Member) -> Member:
        model = self.session.get(MemberModel, entity.member_id)
        if not model:
            raise ValueError(f"Member {entity.member_id} not found")
        model.first_name = entity.first_name
        model.last_name = entity.last_name
        model.email = entity.email
        model.phone = entity.phone
        self.session.commit()
        return entity

    def delete(self, id: str) -> bool:
        model = self.session.get(MemberModel, id)
        if model:
            self.session.delete(model)
            self.session.commit()
            return True
        return False


class DatabasePolicyRepository:
    """SQLAlchemy implementation of policy repository."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, id: str) -> Optional[Policy]:
        model = self.session.get(PolicyModel, id)
        return _to_domain_policy(model) if model else None

    def list(self, **filters) -> List[Policy]:
        query = select(PolicyModel)
        policies = self.session.execute(query).scalars().all()
        return [_to_domain_policy(p) for p in policies]

    def add(self, entity: Policy) -> Policy:
        # Create policy model
        policy_model = PolicyModel(
            policy_id=entity.policy_id,
            member_id=entity.member_id,
            policy_number=entity.policy_number,
            group_number=entity.group_number,
            policy_start=entity.period.start if entity.period else date.today(),
            policy_end=entity.period.end if entity.period else date.today(),
        )
        self.session.add(policy_model)

        # Add coverage rules
        for rule in entity.coverage_rules:
            rule_model = CoverageRuleModel(
                rule_id=rule.rule_id,
                policy_id=entity.policy_id,
                service_type=rule.service_type,
                coverage_percentage=float(rule.coverage_percentage),
                limit_type=rule.limit_type,
                limit_amount=float(rule.limit_amount.amount),
                deductible_applies=rule.deductible_applies,
                deductible_amount=float(rule.deductible_amount.amount),
                effective_date=rule.effective_date,
                expiration_date=rule.expiration_date,
            )
            self.session.add(rule_model)

        self.session.commit()
        return entity

    def update(self, entity: Policy) -> Policy:
        model = self.session.get(PolicyModel, entity.policy_id)
        if not model:
            raise ValueError(f"Policy {entity.policy_id} not found")
        model.group_number = entity.group_number
        model.policy_start = entity.period.start if entity.period else model.policy_start
        model.policy_end = entity.period.end if entity.period else model.policy_end
        model.updated_at = datetime.utcnow()
        self.session.commit()
        return entity

    def delete(self, id: str) -> bool:
        model = self.session.get(PolicyModel, id)
        if model:
            self.session.delete(model)
            self.session.commit()
            return True
        return False

    def get_by_member(self, member_id: str) -> Optional[Policy]:
        model = self.session.execute(
            select(PolicyModel).where(PolicyModel.member_id == member_id)
        ).scalar_one_or_none()
        return _to_domain_policy(model) if model else None


class DatabaseClaimRepository:
    """SQLAlchemy implementation of claim repository."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, id: str) -> Optional[Claim]:
        model = self.session.get(ClaimModel, id)
        return _to_domain_claim(model) if model else None

    def list(self, **filters) -> List[Claim]:
        query = select(ClaimModel)
        claims = self.session.execute(query).scalars().all()
        return [_to_domain_claim(c) for c in claims]

    def add(self, entity: Claim) -> Claim:
        # Create claim model
        claim_model = ClaimModel(
            claim_id=entity.claim_id,
            member_id=entity.member_id,
            policy_id=entity.policy_id,
            claim_number=entity.claim_number,
            status=entity.status,
            diagnosis_codes=_json_serialize(entity.diagnosis_codes),
            accident_date=entity.accident_date,
            accident_description=entity.accident_description,
            total_requested=float(entity.total_requested.amount),
            total_approved=float(entity.total_approved.amount),
            total_denied=float(entity.total_denied.amount),
            submitted_at=entity.submitted_at,
        )
        self.session.add(claim_model)

        # Add line items
        for item in entity.line_items:
            provider_model = None
            if item.provider:
                provider_model = ProviderModel(
                    provider_id=item.provider.provider_id,
                    name=item.provider.name,
                    npi=item.provider.npi,
                    specialty=item.provider.specialty,
                    address=item.provider.address,
                    phone=item.provider.phone,
                )
                self.session.add(provider_model)
                self.session.flush()  # Get provider_id

            line_item_model = LineItemModel(
                line_item_id=item.line_item_id,
                claim_id=entity.claim_id,
                provider_id=provider_model.provider_id if provider_model else None,
                service_type=item.service_type,
                service_date=item.service_date,
                description=item.description,
                amount=float(item.amount.amount),
                diagnosis_codes=_json_serialize(item.diagnosis_codes),
                status=item.status,
            )
            self.session.add(line_item_model)

        self.session.commit()
        return entity

    def update(self, entity: Claim) -> Claim:
        model = self.session.get(ClaimModel, entity.claim_id)
        if not model:
            raise ValueError(f"Claim {entity.claim_id} not found")
        model.status = entity.status
        model.total_requested = float(entity.total_requested.amount)
        model.total_approved = float(entity.total_approved.amount)
        model.total_denied = float(entity.total_denied.amount)
        model.reviewed_at = entity.reviewed_at
        model.decided_at = entity.decided_at
        model.paid_at = entity.paid_at
        self.session.commit()

        # Update line items
        for item in entity.line_items:
            item_model = self.session.get(LineItemModel, item.line_item_id)
            if item_model:
                item_model.status = item.status
                item_model.adjudicated_amount = float(item.adjudicated_amount.amount) if item.adjudicated_amount else None
                item_model.denied_amount = float(item.denied_amount.amount) if item.denied_amount else None
                item_model.denial_reason = item.denial_reason
                item_model.notes = item.notes

        self.session.commit()
        return entity

    def delete(self, id: str) -> bool:
        model = self.session.get(ClaimModel, id)
        if model:
            self.session.delete(model)
            self.session.commit()
            return True
        return False

    def get_by_member(self, member_id: str) -> List[Claim]:
        query = select(ClaimModel).where(ClaimModel.member_id == member_id)
        models = self.session.execute(query).scalars().all()
        return [_to_domain_claim(m) for m in models]

    def get_by_claim_number(self, claim_number: str) -> Optional[Claim]:
        model = self.session.execute(
            select(ClaimModel).where(ClaimModel.claim_number == claim_number)
        ).scalar_one_or_none()
        return _to_domain_claim(model) if model else None


class DatabaseDisputeRepository:
    """SQLAlchemy implementation of dispute repository."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, id: str) -> Optional[Dispute]:
        model = self.session.get(DisputeModel, id)
        return _to_domain_dispute(model) if model else None

    def list(self, **filters) -> List[Dispute]:
        query = select(DisputeModel)
        disputes = self.session.execute(query).scalars().all()
        return [_to_domain_dispute(d) for d in disputes]

    def add(self, entity: Dispute) -> Dispute:
        model = DisputeModel(
            dispute_id=entity.dispute_id,
            claim_id=entity.claim_id,
            member_id=entity.member_id,
            line_item_ids=_json_serialize(entity.line_item_ids),
            reason=entity.reason,
            supporting_documents=_json_serialize(entity.supporting_documents),
            status=entity.status,
        )
        self.session.add(model)
        self.session.commit()
        return entity

    def update(self, entity: Dispute) -> Dispute:
        model = self.session.get(DisputeModel, entity.dispute_id)
        if not model:
            raise ValueError(f"Dispute {entity.dispute_id} not found")
        model.status = entity.status
        model.resolution_notes = entity.resolution_notes
        model.resolved_at = entity.resolved_at
        model.reviewed_at = entity.reviewed_at
        self.session.commit()
        return entity

    def delete(self, id: str) -> bool:
        model = self.session.get(DisputeModel, id)
        if model:
            self.session.delete(model)
            self.session.commit()
            return True
        return False

    def get_by_claim(self, claim_id: str) -> List[Dispute]:
        query = select(DisputeModel).where(DisputeModel.claim_id == claim_id)
        models = self.session.execute(query).scalars().all()
        return [_to_domain_dispute(m) for m in models]


class DatabaseUsageRepository:
    """SQLAlchemy implementation of usage record repository."""

    def __init__(self, session: Session):
        self.session = session

    def get(self, id: str) -> Optional[UsageRecord]:
        # Usage records don't have string IDs, use integer id
        return None

    def list(self, **filters) -> List[UsageRecord]:
        query = select(UsageRecordModel)
        records = self.session.execute(query).scalars().all()
        return [_to_domain_usage_record(r) for r in records]

    def add(self, entity: UsageRecord) -> UsageRecord:
        raise NotImplementedError("Use add_record instead")

    def update(self, entity: UsageRecord) -> UsageRecord:
        raise NotImplementedError("Usage records are immutable")

    def delete(self, id: str) -> bool:
        raise NotImplementedError("Usage records cannot be deleted")

    def add_record(self, member_id: str, record: UsageRecord) -> None:
        model = UsageRecordModel(
            member_id=member_id,
            service_type=record.service_type,
            service_date=record.service_date,
            amount_paid=float(record.amount_paid.amount),
            rule_id=record.rule_id,
        )
        self.session.add(model)
        self.session.commit()

    def get_by_member(self, member_id: str) -> List[UsageRecord]:
        query = select(UsageRecordModel).where(
            UsageRecordModel.member_id == member_id
        )
        models = self.session.execute(query).scalars().all()
        return [_to_domain_usage_record(m) for m in models]


class DatabaseUnitOfWork:
    """
    Unit of Work pattern for database-backed operations.

    Usage:
        with DatabaseUnitOfWork() as uow:
            member = uow.members.get("member-123")
            uow.claims.add(claim)
    """

    def __init__(self, session: Optional[Session] = None):
        from app.database import SessionLocal

        self._session = session or SessionLocal()
        self._members = None
        self._policies = None
        self._claims = None
        self._disputes = None
        self._usage = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self._session.rollback()
        self._session.close()

    @property
    def members(self) -> DatabaseMemberRepository:
        if self._members is None:
            self._members = DatabaseMemberRepository(self._session)
        return self._members

    @property
    def policies(self) -> DatabasePolicyRepository:
        if self._policies is None:
            self._policies = DatabasePolicyRepository(self._session)
        return self._policies

    @property
    def claims(self) -> DatabaseClaimRepository:
        if self._claims is None:
            self._claims = DatabaseClaimRepository(self._session)
        return self._claims

    @property
    def disputes(self) -> DatabaseDisputeRepository:
        if self._disputes is None:
            self._disputes = DatabaseDisputeRepository(self._session)
        return self._disputes

    @property
    def usage(self) -> DatabaseUsageRepository:
        if self._usage is None:
            self._usage = DatabaseUsageRepository(self._session)
        return self._usage

    def commit(self):
        """Commit all pending changes."""
        self._session.commit()

    def rollback(self):
        """Rollback all pending changes."""
        self._session.rollback()
