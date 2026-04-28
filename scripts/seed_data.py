"""
Database Seeder for Claims Processing System

Populates the database with sample members, policies, claims, and disputes.

Usage:
    python -m scripts.seed_data
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import sys
sys.path.insert(0, '.')

from app.database import init_db, SessionLocal, engine
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
from app.domain.enums import (
    ServiceType,
    CoverageLimitType,
    ClaimStatus,
    LineItemStatus,
    DisputeStatus,
)


def seed_database():
    """Seed the database with sample data."""
    print("Initializing database...")
    init_db()

    db = SessionLocal()
    try:
        # Check if already seeded
        existing_members = db.query(MemberModel).count()
        if existing_members > 0:
            print(f"Database already has {existing_members} members. Skipping seed.")
            return

        print("Seeding database with sample data...\n")

        # ============== MEMBERS ==============
        print("Creating members...")
        members = [
            MemberModel(
                member_id=str(uuid4()),
                first_name="John",
                last_name="Smith",
                date_of_birth=date(1985, 3, 15),
                email="john.smith@email.com",
                phone="555-0101",
            ),
            MemberModel(
                member_id=str(uuid4()),
                first_name="Sarah",
                last_name="Johnson",
                date_of_birth=date(1990, 7, 22),
                email="sarah.j@email.com",
                phone="555-0102",
            ),
            MemberModel(
                member_id=str(uuid4()),
                first_name="Michael",
                last_name="Williams",
                date_of_birth=date(1978, 11, 8),
                email="m.williams@email.com",
                phone="555-0103",
            ),
            MemberModel(
                member_id=str(uuid4()),
                first_name="Emily",
                last_name="Brown",
                date_of_birth=date(1995, 2, 28),
                email="emily.brown@email.com",
                phone="555-0104",
            ),
            MemberModel(
                member_id=str(uuid4()),
                first_name="David",
                last_name="Davis",
                date_of_birth=date(1982, 9, 14),
                email="david.davis@email.com",
                phone="555-0105",
            ),
        ]
        for member in members:
            db.add(member)
        db.commit()
        print(f"  Created {len(members)} members\n")

        # ============== POLICIES WITH COVERAGE RULES ==============
        print("Creating policies with coverage rules...")

        # Policy 1: John Smith - Gold Plan
        policy1 = PolicyModel(
            policy_id=str(uuid4()),
            member_id=members[0].member_id,
            policy_number="POL-2026-GOLD-001",
            group_number="GRP-CORP-001",
            policy_start=date(2026, 1, 1),
            policy_end=date(2026, 12, 31),
        )
        db.add(policy1)
        db.flush()

        # Gold Plan Coverage Rules
        gold_rules = [
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy1.policy_id,
                service_type=ServiceType.PREVENTIVE,
                coverage_percentage=1.0,  # 100%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("2000.00"),
                deductible_applies=False,
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy1.policy_id,
                service_type=ServiceType.PRIMARY_CARE,
                coverage_percentage=0.9,  # 90%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("5000.00"),
                deductible_applies=True,
                deductible_amount=Decimal("250.00"),
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy1.policy_id,
                service_type=ServiceType.SPECIALIST,
                coverage_percentage=0.8,  # 80%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("10000.00"),
                deductible_applies=True,
                deductible_amount=Decimal("250.00"),
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy1.policy_id,
                service_type=ServiceType.LABORATORY,
                coverage_percentage=1.0,  # 100%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("3000.00"),
                deductible_applies=False,
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy1.policy_id,
                service_type=ServiceType.PHYSICAL_THERAPY,
                coverage_percentage=0.7,  # 70%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("2000.00"),
                deductible_applies=False,
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy1.policy_id,
                service_type=ServiceType.EMERGENCY,
                coverage_percentage=0.9,  # 90%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("50000.00"),
                deductible_applies=True,
                deductible_amount=Decimal("500.00"),
            ),
        ]
        for rule in gold_rules:
            db.add(rule)

        # Policy 2: Sarah Johnson - Silver Plan
        policy2 = PolicyModel(
            policy_id=str(uuid4()),
            member_id=members[1].member_id,
            policy_number="POL-2026-SILVER-002",
            group_number="GRP-CORP-002",
            policy_start=date(2026, 1, 1),
            policy_end=date(2026, 12, 31),
        )
        db.add(policy2)
        db.flush()

        silver_rules = [
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy2.policy_id,
                service_type=ServiceType.PREVENTIVE,
                coverage_percentage=1.0,
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("1000.00"),
                deductible_applies=False,
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy2.policy_id,
                service_type=ServiceType.PRIMARY_CARE,
                coverage_percentage=0.7,  # 70%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("3000.00"),
                deductible_applies=True,
                deductible_amount=Decimal("500.00"),
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy2.policy_id,
                service_type=ServiceType.SPECIALIST,
                coverage_percentage=0.6,  # 60%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("6000.00"),
                deductible_applies=True,
                deductible_amount=Decimal("500.00"),
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy2.policy_id,
                service_type=ServiceType.LABORATORY,
                coverage_percentage=0.8,  # 80%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("2000.00"),
                deductible_applies=False,
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy2.policy_id,
                service_type=ServiceType.EMERGENCY,
                coverage_percentage=0.7,  # 70%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("30000.00"),
                deductible_applies=True,
                deductible_amount=Decimal("1000.00"),
            ),
        ]
        for rule in silver_rules:
            db.add(rule)

        # Policy 3: Michael Williams - Bronze Plan
        policy3 = PolicyModel(
            policy_id=str(uuid4()),
            member_id=members[2].member_id,
            policy_number="POL-2026-BRONZE-003",
            group_number="GRP-CORP-003",
            policy_start=date(2026, 1, 1),
            policy_end=date(2026, 12, 31),
        )
        db.add(policy3)
        db.flush()

        bronze_rules = [
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy3.policy_id,
                service_type=ServiceType.PREVENTIVE,
                coverage_percentage=0.8,  # 80%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("500.00"),
                deductible_applies=False,
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy3.policy_id,
                service_type=ServiceType.PRIMARY_CARE,
                coverage_percentage=0.5,  # 50%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("2000.00"),
                deductible_applies=True,
                deductible_amount=Decimal("1000.00"),
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy3.policy_id,
                service_type=ServiceType.EMERGENCY,
                coverage_percentage=0.5,  # 50%
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("20000.00"),
                deductible_applies=True,
                deductible_amount=Decimal("2000.00"),
            ),
        ]
        for rule in bronze_rules:
            db.add(rule)

        # Policy 4: Emily Brown - Platinum Plan
        policy4 = PolicyModel(
            policy_id=str(uuid4()),
            member_id=members[3].member_id,
            policy_number="POL-2026-PLAT-004",
            group_number="GRP-EXEC-001",
            policy_start=date(2026, 1, 1),
            policy_end=date(2026, 12, 31),
        )
        db.add(policy4)
        db.flush()

        platinum_rules = [
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy4.policy_id,
                service_type=ServiceType.PREVENTIVE,
                coverage_percentage=1.0,
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("5000.00"),
                deductible_applies=False,
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy4.policy_id,
                service_type=ServiceType.PRIMARY_CARE,
                coverage_percentage=1.0,
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("10000.00"),
                deductible_applies=False,
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy4.policy_id,
                service_type=ServiceType.SPECIALIST,
                coverage_percentage=0.95,
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("20000.00"),
                deductible_applies=False,
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy4.policy_id,
                service_type=ServiceType.SURGERY,
                coverage_percentage=0.9,
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("100000.00"),
                deductible_applies=False,
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy4.policy_id,
                service_type=ServiceType.MENTAL_HEALTH,
                coverage_percentage=0.9,
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("10000.00"),
                deductible_applies=False,
            ),
        ]
        for rule in platinum_rules:
            db.add(rule)

        # Policy 5: David Davis - Silver Plan (No claims yet)
        policy5 = PolicyModel(
            policy_id=str(uuid4()),
            member_id=members[4].member_id,
            policy_number="POL-2026-SILVER-005",
            group_number="GRP-CORP-002",
            policy_start=date(2026, 1, 1),
            policy_end=date(2026, 12, 31),
        )
        db.add(policy5)
        db.flush()

        silver_rules_2 = [
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy5.policy_id,
                service_type=ServiceType.PREVENTIVE,
                coverage_percentage=1.0,
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("1000.00"),
                deductible_applies=False,
            ),
            CoverageRuleModel(
                rule_id=str(uuid4()),
                policy_id=policy5.policy_id,
                service_type=ServiceType.PRIMARY_CARE,
                coverage_percentage=0.7,
                limit_type=CoverageLimitType.ANNUAL_MAX,
                limit_amount=Decimal("3000.00"),
                deductible_applies=True,
                deductible_amount=Decimal("500.00"),
            ),
        ]
        for rule in silver_rules_2:
            db.add(rule)

        db.commit()
        print(f"  Created 5 policies with {len(gold_rules) + len(silver_rules) + len(bronze_rules) + len(platinum_rules) + len(silver_rules_2)} coverage rules\n")

        # ============== PROVIDERS ==============
        print("Creating providers...")
        providers = [
            ProviderModel(
                provider_id=str(uuid4()),
                name="Dr. Alice Chen",
                npi="1234567890",
                specialty="Primary Care",
                address="123 Medical Plaza, Suite 100",
                phone="555-1001",
            ),
            ProviderModel(
                provider_id=str(uuid4()),
                name="Dr. Robert Martinez",
                npi="2345678901",
                specialty="Cardiology",
                address="456 Heart Center Blvd",
                phone="555-1002",
            ),
            ProviderModel(
                provider_id=str(uuid4()),
                name="City General Hospital",
                npi="3456789012",
                specialty="Emergency",
                address="789 Emergency Way",
                phone="555-1003",
            ),
            ProviderModel(
                provider_id=str(uuid4()),
                name="LabCorp Diagnostics",
                npi="4567890123",
                specialty="Laboratory",
                address="321 Lab Drive",
                phone="555-1004",
            ),
            ProviderModel(
                provider_id=str(uuid4()),
                name="Dr. Susan Lee",
                npi="5678901234",
                specialty="Physical Therapy",
                address="654 Recovery Lane",
                phone="555-1005",
            ),
        ]
        for provider in providers:
            db.add(provider)
        db.commit()
        print(f"  Created {len(providers)} providers\n")

        # ============== CLAIMS ==============
        print("Creating claims...")

        # Claim 1: John Smith - Preventive care (fully approved)
        claim1 = ClaimModel(
            claim_id=str(uuid4()),
            member_id=members[0].member_id,
            policy_id=policy1.policy_id,
            claim_number=f"CLM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-0001",
            status=ClaimStatus.APPROVED,
            diagnosis_codes='["Z00.00"]',
            total_requested=Decimal("200.00"),
            total_approved=Decimal("200.00"),
            total_denied=Decimal("0.00"),
            submitted_at=datetime.now(timezone.utc),
            decided_at=datetime.now(timezone.utc),
        )
        db.add(claim1)
        db.flush()

        claim1_line_items = [
            LineItemModel(
                line_item_id=str(uuid4()),
                claim_id=claim1.claim_id,
                provider_id=providers[0].provider_id,
                service_type=ServiceType.PREVENTIVE,
                service_date=date(2026, 4, 15),
                description="Annual physical examination",
                amount=Decimal("200.00"),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Decimal("200.00"),
                denied_amount=Decimal("0.00"),
                notes="Fully covered under preventive care",
            ),
        ]
        for item in claim1_line_items:
            db.add(item)

        # Claim 2: John Smith - Specialist visit with lab work (partially approved)
        claim2 = ClaimModel(
            claim_id=str(uuid4()),
            member_id=members[0].member_id,
            policy_id=policy1.policy_id,
            claim_number=f"CLM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-0002",
            status=ClaimStatus.PARTIALLY_APPROVED,
            diagnosis_codes='["R07.9"]',
            total_requested=Decimal("650.00"),
            total_approved=Decimal("520.00"),
            total_denied=Decimal("130.00"),
            submitted_at=datetime.now(timezone.utc),
            decided_at=datetime.now(timezone.utc),
        )
        db.add(claim2)
        db.flush()

        claim2_line_items = [
            LineItemModel(
                line_item_id=str(uuid4()),
                claim_id=claim2.claim_id,
                provider_id=providers[1].provider_id,
                service_type=ServiceType.SPECIALIST,
                service_date=date(2026, 4, 20),
                description="Cardiology consultation",
                amount=Decimal("400.00"),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Decimal("320.00"),
                denied_amount=Decimal("80.00"),
                denial_reason="20% coinsurance applied",
                notes="80% covered under specialist benefit",
            ),
            LineItemModel(
                line_item_id=str(uuid4()),
                claim_id=claim2.claim_id,
                provider_id=providers[3].provider_id,
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 4, 20),
                description="Blood panel - comprehensive",
                amount=Decimal("250.00"),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Decimal("250.00"),
                denied_amount=Decimal("0.00"),
                notes="Fully covered - preventive lab work",
            ),
            LineItemModel(
                line_item_id=str(uuid4()),
                claim_id=claim2.claim_id,
                provider_id=providers[1].provider_id,
                service_type=ServiceType.COSMETIC,
                service_date=date(2026, 4, 20),
                description="Cosmetic procedure - not medically necessary",
                amount=Decimal("130.00"),
                status=LineItemStatus.DENIED,
                adjudicated_amount=Decimal("0.00"),
                denied_amount=Decimal("130.00"),
                denial_reason="Service not covered under policy",
                notes="Cosmetic procedures excluded",
            ),
        ]
        for item in claim2_line_items:
            db.add(item)

        # Claim 3: Sarah Johnson - Emergency room visit (large claim)
        claim3 = ClaimModel(
            claim_id=str(uuid4()),
            member_id=members[1].member_id,
            policy_id=policy2.policy_id,
            claim_number=f"CLM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-0003",
            status=ClaimStatus.APPROVED,
            diagnosis_codes='["S83.001A"]',
            accident_date=date(2026, 4, 10),
            accident_description="Slipped and fell while hiking",
            total_requested=Decimal("5500.00"),
            total_approved=Decimal("3150.00"),
            total_denied=Decimal("2350.00"),
            submitted_at=datetime.now(timezone.utc),
            decided_at=datetime.now(timezone.utc),
        )
        db.add(claim3)
        db.flush()

        claim3_line_items = [
            LineItemModel(
                line_item_id=str(uuid4()),
                claim_id=claim3.claim_id,
                provider_id=providers[2].provider_id,
                service_type=ServiceType.EMERGENCY,
                service_date=date(2026, 4, 10),
                description="Emergency room visit - Level 4",
                amount=Decimal("3500.00"),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Decimal("2100.00"),
                denied_amount=Decimal("1400.00"),
                denial_reason="70% coverage after $1000 deductible",
                notes="Deductible applied, 70% coinsurance",
            ),
            LineItemModel(
                line_item_id=str(uuid4()),
                claim_id=claim3.claim_id,
                provider_id=providers[3].provider_id,
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 4, 10),
                description="X-ray and MRI",
                amount=Decimal("1500.00"),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Decimal("1050.00"),
                denied_amount=Decimal("450.00"),
                denial_reason="70% coverage",
                notes="80% covered under lab benefit",
            ),
            LineItemModel(
                line_item_id=str(uuid4()),
                claim_id=claim3.claim_id,
                provider_id=providers[2].provider_id,
                service_type=ServiceType.PHYSICAL_THERAPY,
                service_date=date(2026, 4, 10),
                description="Physical therapy referral",
                amount=Decimal("500.00"),
                status=LineItemStatus.DENIED,
                adjudicated_amount=Decimal("0.00"),
                denied_amount=Decimal("500.00"),
                denial_reason="Service not covered under Silver plan",
                notes="Physical therapy not included in Silver plan",
            ),
        ]
        for item in claim3_line_items:
            db.add(item)

        # Claim 4: Michael Williams - Denied claim (Bronze plan limitations)
        claim4 = ClaimModel(
            claim_id=str(uuid4()),
            member_id=members[2].member_id,
            policy_id=policy3.policy_id,
            claim_number=f"CLM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-0004",
            status=ClaimStatus.DENIED,
            diagnosis_codes='["F32.9"]',
            total_requested=Decimal("1500.00"),
            total_approved=Decimal("0.00"),
            total_denied=Decimal("1500.00"),
            submitted_at=datetime.now(timezone.utc),
            decided_at=datetime.now(timezone.utc),
        )
        db.add(claim4)
        db.flush()

        claim4_line_items = [
            LineItemModel(
                line_item_id=str(uuid4()),
                claim_id=claim4.claim_id,
                provider_id=str(uuid4()),  # Out of network
                service_type=ServiceType.MENTAL_HEALTH,
                service_date=date(2026, 4, 5),
                description="Psychiatric consultation",
                amount=Decimal("1500.00"),
                status=LineItemStatus.DENIED,
                adjudicated_amount=Decimal("0.00"),
                denied_amount=Decimal("1500.00"),
                denial_reason="Mental health services not covered under Bronze plan",
                notes="No mental health coverage in Bronze plan",
            ),
        ]
        for item in claim4_line_items:
            db.add(item)

        # Claim 5: Emily Brown - Surgery claim (Platinum plan)
        claim5 = ClaimModel(
            claim_id=str(uuid4()),
            member_id=members[3].member_id,
            policy_id=policy4.policy_id,
            claim_number=f"CLM-{datetime.now(timezone.utc).strftime('%Y%m%d')}-0005",
            status=ClaimStatus.PAID,
            diagnosis_codes='["K80.20"]',
            total_requested=Decimal("25000.00"),
            total_approved=Decimal("22500.00"),
            total_denied=Decimal("2500.00"),
            submitted_at=datetime.now(timezone.utc),
            decided_at=datetime.now(timezone.utc),
            paid_at=datetime.now(timezone.utc),
        )
        db.add(claim5)
        db.flush()

        claim5_line_items = [
            LineItemModel(
                line_item_id=str(uuid4()),
                claim_id=claim5.claim_id,
                provider_id=str(uuid4()),
                service_type=ServiceType.SURGERY,
                service_date=date(2026, 3, 15),
                description="Laparoscopic cholecystectomy",
                amount=Decimal("20000.00"),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Decimal("18000.00"),
                denied_amount=Decimal("2000.00"),
                notes="90% covered under surgery benefit",
            ),
            LineItemModel(
                line_item_id=str(uuid4()),
                claim_id=claim5.claim_id,
                provider_id=providers[2].provider_id,
                service_type=ServiceType.INPATIENT,
                service_date=date(2026, 3, 15),
                description="Hospital stay - 2 days",
                amount=Decimal("5000.00"),
                status=LineItemStatus.APPROVED,
                adjudicated_amount=Decimal("4500.00"),
                denied_amount=Decimal("500.00"),
                notes="90% covered under inpatient benefit",
            ),
        ]
        for item in claim5_line_items:
            db.add(item)

        db.commit()
        print(f"  Created 5 claims with multiple line items\n")

        # ============== DISPUTES ==============
        print("Creating disputes...")

        # Dispute 1: Michael Williams disputing denied mental health claim
        dispute1 = DisputeModel(
            dispute_id=str(uuid4()),
            claim_id=claim4.claim_id,
            member_id=members[2].member_id,
            line_item_ids='["' + claim4_line_items[0].line_item_id + '"]',
            reason="I believe mental health services should be covered. My employer confirmed that mental health is an essential health benefit that should be included in all plans under ACA requirements. I am requesting a review of this denial.",
            status=DisputeStatus.UNDER_REVIEW,
            created_at=datetime.now(timezone.utc),
        )
        db.add(dispute1)

        # Dispute 2: Sarah Johnson disputing physical therapy denial
        dispute2 = DisputeModel(
            dispute_id=str(uuid4()),
            claim_id=claim3.claim_id,
            member_id=members[1].member_id,
            line_item_ids='["' + claim3_line_items[2].line_item_id + '"]',
            reason="The physical therapy was medically necessary following my emergency room visit for a knee injury. The ER doctor specifically recommended PT as part of my recovery. I request that this claim be reconsidered as post-acute care.",
            supporting_documents='["er_discharge_summary.pdf", "physician_referral.pdf"]',
            status=DisputeStatus.OPEN,
            created_at=datetime.now(timezone.utc),
        )
        db.add(dispute2)

        db.commit()
        print(f"  Created 2 disputes\n")

        # ============== USAGE RECORDS ==============
        print("Creating usage records...")

        usage_records = [
            UsageRecordModel(
                member_id=members[0].member_id,
                service_type=ServiceType.PREVENTIVE,
                service_date=date(2026, 4, 15),
                amount_paid=Decimal("200.00"),
                rule_id="rule-preventive-001",
            ),
            UsageRecordModel(
                member_id=members[0].member_id,
                service_type=ServiceType.SPECIALIST,
                service_date=date(2026, 4, 20),
                amount_paid=Decimal("320.00"),
                rule_id="rule-specialist-001",
            ),
            UsageRecordModel(
                member_id=members[0].member_id,
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 4, 20),
                amount_paid=Decimal("250.00"),
                rule_id="rule-lab-001",
            ),
            UsageRecordModel(
                member_id=members[1].member_id,
                service_type=ServiceType.EMERGENCY,
                service_date=date(2026, 4, 10),
                amount_paid=Decimal("2100.00"),
                rule_id="rule-emergency-001",
            ),
            UsageRecordModel(
                member_id=members[1].member_id,
                service_type=ServiceType.LABORATORY,
                service_date=date(2026, 4, 10),
                amount_paid=Decimal("1050.00"),
                rule_id="rule-lab-002",
            ),
            UsageRecordModel(
                member_id=members[3].member_id,
                service_type=ServiceType.SURGERY,
                service_date=date(2026, 3, 15),
                amount_paid=Decimal("18000.00"),
                rule_id="rule-surgery-001",
            ),
            UsageRecordModel(
                member_id=members[3].member_id,
                service_type=ServiceType.INPATIENT,
                service_date=date(2026, 3, 15),
                amount_paid=Decimal("4500.00"),
                rule_id="rule-inpatient-001",
            ),
        ]
        for record in usage_records:
            db.add(record)

        db.commit()
        print(f"  Created {len(usage_records)} usage records\n")

        # ============== SUMMARY ==============
        print("=" * 50)
        print("DATABASE SEEDING COMPLETE")
        print("=" * 50)
        print(f"""
Summary:
  - Members:    {len(members)}
  - Policies:   5 (Gold, Silver, Bronze, Platinum, Silver)
  - Providers:  {len(providers)}
  - Claims:     5 (1 approved, 1 partially approved, 1 denied, 1 paid, 1 pending)
  - Disputes:   2 (1 under review, 1 open)
  - Usage:      {len(usage_records)} records

Sample API calls:
  GET /api/v1/members          - List all members
  GET /api/v1/members/{{id}}    - Get specific member
  GET /api/v1/members/{{id}}/policy - Get member's policy
  GET /api/v1/claims           - List all claims
  GET /api/v1/claims/{{id}}/explanation - Get claim explanation
  GET /api/v1/claims/{{id}}/disputes - Get claim disputes
""")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
