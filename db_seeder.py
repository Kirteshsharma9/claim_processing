"""
seed_claims_sqlite.py

Generic SQLite Seeder for Claims Processing System

Features:
- Supports ALL enums provided
- Inserts into every table
- Safe re-run using INSERT OR IGNORE
- Handles timestamps properly
- Random realistic data
- JSON fields stored as TEXT
- Foreign key safe
- Works directly with sqlite3

Run:
    python seed_claims_sqlite.py
"""

import sqlite3
import json
import random
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timedelta, date
from enum import Enum


# =========================================================
# ENUMS
# =========================================================

class ClaimStatus(str, Enum):
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    DENIED = "denied"
    PAID = "paid"
    APPEAL = "appeal"


class LineItemStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    NEEDS_REVIEW = "needs_review"


class ServiceType(str, Enum):
    PRIMARY_CARE = "primary_care"
    SPECIALIST = "specialist"
    EMERGENCY = "emergency"
    URGENT_CARE = "urgent_care"
    INPATIENT = "inpatient"
    OUTPATIENT = "outpatient"
    SURGERY = "surgery"
    IMAGING = "imaging"
    LABORATORY = "laboratory"
    PHYSICAL_THERAPY = "physical_therapy"
    PRESCRIPTION = "prescription"
    MENTAL_HEALTH = "mental_health"
    PREVENTIVE = "preventive"
    COSMETIC = "cosmetic"
    OTHER = "other"


class CoverageLimitType(str, Enum):
    PER_OCCURRENCE = "per_occurrence"
    PER_VISIT = "per_visit"
    ANNUAL_MAX = "annual_max"
    PER_CALENDAR_YEAR = "per_calendar_year"
    LIFETIME_MAX = "lifetime_max"


class DisputeStatus(str, Enum):
    OPEN = "open"
    UNDER_REVIEW = "under_review"
    RESOLVED = "resolved"
    OVERTURNED = "overturned"
    CLOSED = "closed"


# =========================================================
# CONFIG
# =========================================================

DB_NAME = "claims.db"
MEMBER_COUNT = 50
PROVIDER_COUNT = 20
CLAIM_COUNT = 300


# =========================================================
# HELPERS
# =========================================================

def uid():
    return str(uuid4())


def now():
    return datetime.utcnow()


def ts():
    return now().strftime("%Y-%m-%d %H:%M:%S")


def rand_date(days=365):
    return date.today() - timedelta(days=random.randint(0, days))


def rand_dt(days=365):
    return now() - timedelta(days=random.randint(0, days))


def money(min_val=10, max_val=5000):
    return round(random.uniform(min_val, max_val), 2)


def j(value):
    return json.dumps(value)


# =========================================================
# STATIC DATA
# =========================================================

FIRST = ["Kirtesh", "Raj", "Amit", "Priya", "Neha", "Rohan", "Vikas"]
LAST = ["Sharma", "Patel", "Gupta", "Jain", "Verma", "Singh"]
SPECIALTIES = [
    "Cardiology", "Orthopedic", "General Medicine",
    "Dentist", "Neurology", "Radiology"
]


# =========================================================
# MAIN
# =========================================================

def main():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    # -----------------------------------------------------
    # MEMBERS
    # -----------------------------------------------------
    members = []

    for _ in range(MEMBER_COUNT):
        member_id = uid()
        members.append(member_id)

        first = random.choice(FIRST)
        last = random.choice(LAST)

        cur.execute("""
        INSERT OR IGNORE INTO members (
            member_id, first_name, last_name,
            date_of_birth, email, phone, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            member_id,
            first,
            last,
            rand_date(18000),
            f"{first.lower()}.{last.lower()}@mail.com",
            f"98{random.randint(10000000,99999999)}",
            ts()
        ))

    # -----------------------------------------------------
    # PROVIDERS
    # -----------------------------------------------------
    providers = []

    for i in range(PROVIDER_COUNT):
        provider_id = uid()
        providers.append(provider_id)

        cur.execute("""
        INSERT OR IGNORE INTO providers (
            provider_id, name, npi, specialty,
            address, phone
        ) VALUES (?, ?, ?, ?, ?, ?)
        """, (
            provider_id,
            f"Hospital {i+1}",
            str(random.randint(1000000000, 9999999999)),
            random.choice(SPECIALTIES),
            "Bhopal, MP",
            f"91{random.randint(1000000000,9999999999)}"
        ))

    # -----------------------------------------------------
    # POLICIES + COVERAGE RULES
    # -----------------------------------------------------
    policies = []

    for member_id in members:
        policy_id = uid()
        policies.append((policy_id, member_id))

        created_at = ts()

        cur.execute("""
        INSERT OR IGNORE INTO policies (
            policy_id, member_id, policy_number,
            group_number, policy_start, policy_end,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            policy_id,
            member_id,
            f"POL{random.randint(100000,999999)}",
            f"GRP{random.randint(1000,9999)}",
            date.today() - timedelta(days=365),
            date.today() + timedelta(days=365),
            created_at,
            created_at
        ))

        for service in ServiceType:
            cur.execute("""
            INSERT OR IGNORE INTO coverage_rules (
                rule_id, policy_id, service_type,
                coverage_percentage,
                limit_type,
                limit_amount,
                deductible_applies,
                deductible_amount,
                effective_date,
                expiration_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                uid(),
                policy_id,
                service.value,
                round(random.choice([0.60, 0.70, 0.80, 0.90, 1.00]), 4),
                random.choice(list(CoverageLimitType)).value,
                money(500, 20000),
                random.choice([0, 1]),
                money(0, 500),
                date.today() - timedelta(days=365),
                None
            ))

    # -----------------------------------------------------
    # CLAIMS + LINE ITEMS + DISPUTES + USAGE RECORDS
    # -----------------------------------------------------
    for _ in range(CLAIM_COUNT):

        policy_id, member_id = random.choice(policies)
        claim_id = uid()
        claim_status = random.choice(list(ClaimStatus)).value

        created_at = rand_dt(365)
        submitted_at = created_at
        reviewed_at = None
        decided_at = None
        paid_at = None

        if claim_status in ["in_review"]:
            reviewed_at = created_at + timedelta(days=1)

        if claim_status in [
            "approved",
            "partially_approved",
            "denied",
            "appeal"
        ]:
            reviewed_at = created_at + timedelta(days=1)
            decided_at = created_at + timedelta(days=2)

        if claim_status == "paid":
            reviewed_at = created_at + timedelta(days=1)
            decided_at = created_at + timedelta(days=2)
            paid_at = created_at + timedelta(days=4)

        line_count = random.randint(1, 4)

        total_requested = 0
        total_approved = 0
        total_denied = 0
        line_item_ids = []

        cur.execute("""
        INSERT OR IGNORE INTO claims (
            claim_id, member_id, policy_id, claim_number,
            status, diagnosis_codes, accident_date,
            accident_description,
            total_requested, total_approved, total_denied,
            created_at, submitted_at,
            reviewed_at, decided_at, paid_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            claim_id,
            member_id,
            policy_id,
            f"CLM{random.randint(1000000,9999999)}",
            claim_status,
            j(["A10", "B20"]),
            rand_date(100),
            "Minor incident",
            0,
            0,
            0,
            created_at,
            submitted_at,
            reviewed_at,
            decided_at,
            paid_at
        ))

        for _ in range(line_count):

            line_id = uid()
            line_item_ids.append(line_id)

            amount = money(100, 5000)

            if claim_status in ["submitted"]:
                li_status = "pending"
                approved = None
                denied = None

            elif claim_status in ["in_review", "appeal"]:
                li_status = "needs_review"
                approved = None
                denied = None

            elif claim_status in ["approved", "paid"]:
                li_status = "approved"
                approved = amount
                denied = 0

            elif claim_status == "denied":
                li_status = "denied"
                approved = 0
                denied = amount

            else:
                li_status = random.choice(["approved", "denied"])
                if li_status == "approved":
                    approved = round(amount * 0.70, 2)
                    denied = round(amount * 0.30, 2)
                else:
                    approved = 0
                    denied = amount

            total_requested += amount
            total_approved += approved or 0
            total_denied += denied or 0

            service_type = random.choice(list(ServiceType)).value

            cur.execute("""
            INSERT OR IGNORE INTO line_items (
                line_item_id, claim_id, provider_id,
                service_type, service_date,
                description, amount,
                diagnosis_codes,
                status,
                adjudicated_amount,
                denied_amount,
                denial_reason,
                notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                line_id,
                claim_id,
                random.choice(providers),
                service_type,
                rand_date(300),
                "Healthcare service charge",
                amount,
                j(["X10"]),
                li_status,
                approved,
                denied,
                "Coverage denied" if denied else None,
                "Auto seeded"
            ))

            # usage records only when paid/approved
            if approved and approved > 0:
                cur.execute("""
                INSERT INTO usage_records (
                    member_id, service_type,
                    service_date, amount_paid,
                    rule_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    member_id,
                    service_type,
                    rand_date(300),
                    approved,
                    uid(),
                    ts()
                ))

        # update totals
        cur.execute("""
        UPDATE claims
        SET total_requested=?,
            total_approved=?,
            total_denied=?
        WHERE claim_id=?
        """, (
            total_requested,
            total_approved,
            total_denied,
            claim_id
        ))

        # disputes
        if claim_status in ["denied", "partially_approved", "appeal"]:
            if random.random() < 0.35:
                cur.execute("""
                INSERT OR IGNORE INTO disputes (
                    dispute_id, claim_id, member_id,
                    line_item_ids,
                    reason,
                    supporting_documents,
                    status,
                    created_at,
                    reviewed_at,
                    resolved_at,
                    resolution_notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    uid(),
                    claim_id,
                    member_id,
                    j(line_item_ids),
                    "Please re-check adjudication",
                    j(["invoice.pdf"]),
                    random.choice(list(DisputeStatus)).value,
                    ts(),
                    None,
                    None,
                    None
                ))

    conn.commit()
    conn.close()

    print("SQLite dummy data inserted successfully.")


if __name__ == "__main__":
    main()