"""
SQLAlchemy database models for the Claims Processing System.

These models map domain entities to database tables.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Date,
    ForeignKey,
    Column,
    Text,
    Enum as SQLEnum,
    Numeric,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.domain.enums import (
    ClaimStatus,
    LineItemStatus,
    ServiceType,
    CoverageLimitType,
    DisputeStatus,
)


class MemberModel(Base):
    """Database model for Member entity."""

    __tablename__ = "members"

    member_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    policy: Mapped[Optional["PolicyModel"]] = relationship(
        "PolicyModel", back_populates="member", uselist=False, cascade="all, delete-orphan"
    )
    claims: Mapped[List["ClaimModel"]] = relationship(
        "ClaimModel", back_populates="member", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Member(member_id='{self.member_id}', name='{self.first_name} {self.last_name}')>"


class PolicyModel(Base):
    """Database model for Policy entity."""

    __tablename__ = "policies"

    policy_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    member_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("members.member_id"), nullable=False, unique=True
    )
    policy_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    group_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    policy_start: Mapped[date] = mapped_column(Date, nullable=False)
    policy_end: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    member: Mapped["MemberModel"] = relationship("MemberModel", back_populates="policy")
    coverage_rules: Mapped[List["CoverageRuleModel"]] = relationship(
        "CoverageRuleModel", back_populates="policy", cascade="all, delete-orphan"
    )
    claims: Mapped[List["ClaimModel"]] = relationship(
        "ClaimModel", back_populates="policy", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Policy(policy_id='{self.policy_id}', policy_number='{self.policy_number}')>"


class CoverageRuleModel(Base):
    """Database model for CoverageRule entity."""

    __tablename__ = "coverage_rules"

    rule_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("policies.policy_id"), nullable=False
    )
    service_type: Mapped[str] = mapped_column(SQLEnum(ServiceType), nullable=False)
    coverage_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 4), nullable=False
    )  # 0.0000 to 1.0000
    limit_type: Mapped[str] = mapped_column(
        SQLEnum(CoverageLimitType), nullable=False
    )
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deductible_applies: Mapped[bool] = mapped_column(Boolean, default=False)
    deductible_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=0.00
    )
    effective_date: Mapped[date] = mapped_column(Date, default=date.today)
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Relationships
    policy: Mapped["PolicyModel"] = relationship(
        "PolicyModel", back_populates="coverage_rules"
    )

    def __repr__(self) -> str:
        return f"<CoverageRule(rule_id='{self.rule_id}', service_type='{self.service_type}')>"


class ProviderModel(Base):
    """Database model for Provider entity."""

    __tablename__ = "providers"

    provider_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    npi: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    specialty: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relationships
    line_items: Mapped[List["LineItemModel"]] = relationship(
        "LineItemModel", back_populates="provider"
    )

    def __repr__(self) -> str:
        return f"<Provider(provider_id='{self.provider_id}', name='{self.name}')>"


class ClaimModel(Base):
    """Database model for Claim entity."""

    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    member_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("members.member_id"), nullable=False
    )
    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("policies.policy_id"), nullable=False
    )
    claim_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        SQLEnum(ClaimStatus), default=ClaimStatus.SUBMITTED
    )
    diagnosis_codes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array stored as text
    accident_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    accident_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_requested: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0.00)
    total_approved: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0.00)
    total_denied: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0.00)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    member: Mapped["MemberModel"] = relationship("MemberModel", back_populates="claims")
    policy: Mapped["PolicyModel"] = relationship("PolicyModel", back_populates="claims")
    line_items: Mapped[List["LineItemModel"]] = relationship(
        "LineItemModel", back_populates="claim", cascade="all, delete-orphan"
    )
    disputes: Mapped[List["DisputeModel"]] = relationship(
        "DisputeModel", back_populates="claim", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Claim(claim_id='{self.claim_id}', claim_number='{self.claim_number}')>"


class LineItemModel(Base):
    """Database model for LineItem entity."""

    __tablename__ = "line_items"

    line_item_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("claims.claim_id"), nullable=False
    )
    provider_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("providers.provider_id"), nullable=True
    )
    service_type: Mapped[str] = mapped_column(SQLEnum(ServiceType), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    diagnosis_codes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array stored as text
    status: Mapped[str] = mapped_column(
        SQLEnum(LineItemStatus), default=LineItemStatus.PENDING
    )
    adjudicated_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    denied_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    denial_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    claim: Mapped["ClaimModel"] = relationship("ClaimModel", back_populates="line_items")
    provider: Mapped[Optional["ProviderModel"]] = relationship(
        "ProviderModel", back_populates="line_items"
    )

    def __repr__(self) -> str:
        return f"<LineItem(line_item_id='{self.line_item_id}', service_type='{self.service_type}')>"


class DisputeModel(Base):
    """Database model for Dispute entity."""

    __tablename__ = "disputes"

    dispute_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    claim_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("claims.claim_id"), nullable=False
    )
    member_id: Mapped[str] = mapped_column(String(36), nullable=False)
    line_item_ids: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array stored as text
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_documents: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array stored as text
    status: Mapped[str] = mapped_column(
        SQLEnum(DisputeStatus), default=DisputeStatus.OPEN
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    claim: Mapped["ClaimModel"] = relationship("ClaimModel", back_populates="disputes")

    def __repr__(self) -> str:
        return f"<Dispute(dispute_id='{self.dispute_id}', status='{self.status.value}')>"


class UsageRecordModel(Base):
    """Database model for tracking usage against coverage limits."""

    __tablename__ = "usage_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    member_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("members.member_id"), nullable=False
    )
    service_type: Mapped[str] = mapped_column(SQLEnum(ServiceType), nullable=False)
    service_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    rule_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<UsageRecord(id={self.id}, member_id='{self.member_id}', amount={self.amount_paid})>"
