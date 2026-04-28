from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Generic, Optional, TypeVar
from uuid import UUID

from app.domain.models import Member, Policy, Claim, Dispute
from app.services.coverage import UsageRecord


T = TypeVar('T')


class Repository(ABC, Generic[T]):
    """Generic repository interface for CRUD operations."""

    @abstractmethod
    def get(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    def list(self, **filters) -> list[T]:
        """List entities with optional filters."""
        pass

    @abstractmethod
    def add(self, entity: T) -> T:
        """Add a new entity."""
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an existing entity."""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete an entity by ID."""
        pass


class InMemoryMemberRepository(Repository[Member]):
    """In-memory implementation of member repository."""

    def __init__(self):
        self._members: dict[str, Member] = {}

    def get(self, id: str) -> Optional[Member]:
        return self._members.get(id)

    def list(self, **filters) -> list[Member]:
        members = list(self._members.values())
        if filters:
            return [m for m in members if self._matches_filters(m, filters)]
        return members

    def add(self, entity: Member) -> Member:
        if entity.member_id in self._members:
            raise ValueError(f"Member {entity.member_id} already exists")
        self._members[entity.member_id] = entity
        return entity

    def update(self, entity: Member) -> Member:
        if entity.member_id not in self._members:
            raise ValueError(f"Member {entity.member_id} not found")
        self._members[entity.member_id] = entity
        return entity

    def delete(self, id: str) -> bool:
        if id in self._members:
            del self._members[id]
            return True
        return False

    def _matches_filters(self, member: Member, filters: dict) -> bool:
        for key, value in filters.items():
            if not hasattr(member, key) or getattr(member, key) != value:
                return False
        return True


class InMemoryPolicyRepository(Repository[Policy]):
    """In-memory implementation of policy repository."""

    def __init__(self):
        self._policies: dict[str, Policy] = {}
        self._by_member: dict[str, str] = {}  # member_id -> policy_id

    def get(self, id: str) -> Optional[Policy]:
        return self._policies.get(id)

    def list(self, **filters) -> list[Policy]:
        policies = list(self._policies.values())
        if filters:
            return [p for p in policies if self._matches_filters(p, filters)]
        return policies

    def add(self, entity: Policy) -> Policy:
        if entity.policy_id in self._policies:
            raise ValueError(f"Policy {entity.policy_id} already exists")
        self._policies[entity.policy_id] = entity
        self._by_member[entity.member_id] = entity.policy_id
        return entity

    def update(self, entity: Policy) -> Policy:
        if entity.policy_id not in self._policies:
            raise ValueError(f"Policy {entity.policy_id} not found")
        # Update member index if changed
        old_policy = self._policies[entity.policy_id]
        if old_policy.member_id != entity.member_id:
            self._by_member.pop(old_policy.member_id, None)
            self._by_member[entity.member_id] = entity.policy_id
        self._policies[entity.policy_id] = entity
        return entity

    def delete(self, id: str) -> bool:
        if id in self._policies:
            policy = self._policies[id]
            del self._policies[id]
            self._by_member.pop(policy.member_id, None)
            return True
        return False

    def get_by_member(self, member_id: str) -> Optional[Policy]:
        """Get policy for a specific member."""
        policy_id = self._by_member.get(member_id)
        if policy_id:
            return self._policies.get(policy_id)
        return None

    def _matches_filters(self, policy: Policy, filters: dict) -> bool:
        for key, value in filters.items():
            if not hasattr(policy, key) or getattr(policy, key) != value:
                return False
        return True


class InMemoryClaimRepository(Repository[Claim]):
    """In-memory implementation of claim repository."""

    def __init__(self):
        self._claims: dict[str, Claim] = {}
        self._by_member: dict[str, list[str]] = {}  # member_id -> [claim_ids]
        self._claim_numbers: dict[str, str] = {}  # claim_number -> claim_id

    def get(self, id: str) -> Optional[Claim]:
        return self._claims.get(id)

    def list(self, **filters) -> list[Claim]:
        claims = list(self._claims.values())
        if filters:
            return [c for c in claims if self._matches_filters(c, filters)]
        return claims

    def add(self, entity: Claim) -> Claim:
        if entity.claim_id in self._claims:
            raise ValueError(f"Claim {entity.claim_id} already exists")
        self._claims[entity.claim_id] = entity
        self._claim_numbers[entity.claim_number] = entity.claim_id

        if entity.member_id not in self._by_member:
            self._by_member[entity.member_id] = []
        self._by_member[entity.member_id].append(entity.claim_id)

        return entity

    def update(self, entity: Claim) -> Claim:
        if entity.claim_id not in self._claims:
            raise ValueError(f"Claim {entity.claim_id} not found")
        self._claims[entity.claim_id] = entity
        return entity

    def delete(self, id: str) -> bool:
        if id in self._claims:
            claim = self._claims[id]
            del self._claims[id]
            self._claim_numbers.pop(claim.claim_number, None)
            if claim.member_id in self._by_member:
                self._by_member[claim.member_id].remove(id)
            return True
        return False

    def get_by_member(self, member_id: str) -> list[Claim]:
        """Get all claims for a specific member."""
        claim_ids = self._by_member.get(member_id, [])
        return [self._claims[cid] for cid in claim_ids if cid in self._claims]

    def get_by_claim_number(self, claim_number: str) -> Optional[Claim]:
        """Get claim by claim number."""
        claim_id = self._claim_numbers.get(claim_number)
        if claim_id:
            return self._claims.get(claim_id)
        return None

    def _matches_filters(self, claim: Claim, filters: dict) -> bool:
        for key, value in filters.items():
            if not hasattr(claim, key) or getattr(claim, key) != value:
                return False
        return True


class InMemoryDisputeRepository(Repository[Dispute]):
    """In-memory implementation of dispute repository."""

    def __init__(self):
        self._disputes: dict[str, Dispute] = {}
        self._by_claim: dict[str, list[str]] = {}  # claim_id -> [dispute_ids]

    def get(self, id: str) -> Optional[Dispute]:
        return self._disputes.get(id)

    def list(self, **filters) -> list[Dispute]:
        disputes = list(self._disputes.values())
        if filters:
            return [d for d in disputes if self._matches_filters(d, filters)]
        return disputes

    def add(self, entity: Dispute) -> Dispute:
        if entity.dispute_id in self._disputes:
            raise ValueError(f"Dispute {entity.dispute_id} already exists")
        self._disputes[entity.dispute_id] = entity

        if entity.claim_id not in self._by_claim:
            self._by_claim[entity.claim_id] = []
        self._by_claim[entity.claim_id].append(entity.dispute_id)

        return entity

    def update(self, entity: Dispute) -> Dispute:
        if entity.dispute_id not in self._disputes:
            raise ValueError(f"Dispute {entity.dispute_id} not found")
        self._disputes[entity.dispute_id] = entity
        return entity

    def delete(self, id: str) -> bool:
        if id in self._disputes:
            dispute = self._disputes[id]
            del self._disputes[id]
            if dispute.claim_id in self._by_claim:
                self._by_claim[dispute.claim_id].remove(id)
            return True
        return False

    def get_by_claim(self, claim_id: str) -> list[Dispute]:
        """Get all disputes for a specific claim."""
        dispute_ids = self._by_claim.get(claim_id, [])
        return [self._disputes[did] for did in dispute_ids if did in self._disputes]

    def _matches_filters(self, dispute: Dispute, filters: dict) -> bool:
        for key, value in filters.items():
            if not hasattr(dispute, key) or getattr(dispute, key) != value:
                return False
        return True


class InMemoryUsageRepository(Repository[UsageRecord]):
    """In-memory repository for usage history tracking."""

    def __init__(self):
        self._records: list[UsageRecord] = []
        self._by_member: dict[str, list[UsageRecord]] = {}

    def get(self, id: str) -> Optional[UsageRecord]:
        # Usage records don't have IDs, search by index
        for record in self._records:
            if id(record) == id:
                return record
        return None

    def list(self, **filters) -> list[UsageRecord]:
        records = self._records.copy()
        if filters:
            return [r for r in records if self._matches_filters(r, filters)]
        return records

    def add(self, entity: UsageRecord) -> UsageRecord:
        self._records.append(entity)
        return entity

    def update(self, entity: UsageRecord) -> UsageRecord:
        raise NotImplementedError("Usage records are immutable")

    def delete(self, id: str) -> bool:
        raise NotImplementedError("Usage records cannot be deleted")

    def add_record(self, member_id: str, record: UsageRecord) -> None:
        """Add a usage record for a member."""
        if member_id not in self._by_member:
            self._by_member[member_id] = []
        self._by_member[member_id].append(record)
        self._records.append(record)

    def get_by_member(self, member_id: str) -> list[UsageRecord]:
        """Get usage history for a specific member."""
        return self._by_member.get(member_id, [])

    def _matches_filters(self, record: UsageRecord, filters: dict) -> bool:
        for key, value in filters.items():
            if not hasattr(record, key) or getattr(record, key) != value:
                return False
        return True


class UnitOfWork:
    """
    Unit of Work pattern for transactional operations.

    Groups repository operations together for consistency.
    """

    def __init__(self):
        self.members = InMemoryMemberRepository()
        self.policies = InMemoryPolicyRepository()
        self.claims = InMemoryClaimRepository()
        self.disputes = InMemoryDisputeRepository()
        self.usage = InMemoryUsageRepository()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # In a real implementation, this would commit or rollback
        pass
