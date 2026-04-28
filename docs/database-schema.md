# Database Schema

## Overview

This document describes the SQLite database schema for the Claims Processing System. The schema uses SQLAlchemy ORM with declarative models.

## Entity Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLAIMS PROCESSING DATABASE                         │
└─────────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────┐
                              │     members      │
                              ├──────────────────┤
                              │ member_id (PK)   │◄───────────────┐
                              │ first_name       │                │
                              │ last_name        │                │
                              │ date_of_birth    │                │
                              │ email            │                │
                              │ phone            │                │
                              │ created_at       │                │
                              └────────┬─────────┘                │
                                       │                          │
                                       │ 1                        │ 1
                                       │                          │
                                       │                          │
                    ┌──────────────────┼──────────────────┐       │
                    │                  │ 1                 │       │
                    │                  ▼                   │       │
                    │         ┌──────────────────┐         │       │
                    │         │     policies     │         │       │
                    │         ├──────────────────┤         │       │
                    │         │ policy_id (PK)   │         │       │
                    │         │ member_id (FK)   │─────────┘       │
                    │         │ policy_number    │                 │
                    │         │ group_number     │                 │
                    │         │ policy_start     │                 │
                    │         │ policy_end       │                 │
                    │         │ created_at       │                 │
                    │         │ updated_at       │                 │
                    │         └────────┬─────────┘                 │
                    │                  │                            │
                    │                  │ 1                          │
                    │                  │                            │
                    │                  │ *                          │
                    │         ┌────────▼─────────┐                  │
                    │         │ coverage_rules   │                  │
                    │         ├──────────────────┤                  │
                    │         │ rule_id (PK)     │                  │
                    │         │ policy_id (FK)   │                  │
                    │         │ service_type     │                  │
                    │         │ coverage_pct     │                  │
                    │         │ limit_type       │                  │
                    │         │ limit_amount     │                  │
                    │         │ deductible_...   │                  │
                    │         │ effective_date   │                  │
                    │         │ expiration_date  │                  │
                    │         └──────────────────┘                  │
                    │                                               │
                    │                                               │
                    │    ┌─────────────────────────────────────┐   │
                    │    │                 *                   │   │
                    │    ▼                                     │   │
                    │    ┌──────────────────┐                  │   │
                    │    │      claims      │                  │   │
                    │    ├──────────────────┤                  │   │
                    │    │ claim_id (PK)    │                  │   │
                    │    │ member_id (FK)   │──────────────────┘   │
                    │    │ policy_id (FK)   │──────────────────────┘
                    │    │ claim_number     │
                    │    │ status           │
                    │    │ diagnosis_codes  │
                    │    │ accident_date    │
                    │    │ total_requested  │
                    │    │ total_approved   │
                    │    │ total_denied     │
                    │    │ created_at       │
                    │    │ submitted_at     │
                    │    │ reviewed_at      │
                    │    │ decided_at       │
                    │    │ paid_at          │
                    │    └────────┬─────────┘
                    │             │
                    │             │ 1
                    │             │
                    │             │ *
                    │    ┌────────▼─────────┐
                    │    │    line_items    │
                    │    ├──────────────────┤
                    │    │ line_item_id(PK) │
                    │    │ claim_id (FK)    │
                    │    │ provider_id(FK)  │──────┐
                    │    │ service_type     │      │
                    │    │ service_date     │      │
                    │    │ description      │      │
                    │    │ amount           │      │
                    │    │ status           │      │
                    │    │ adjudicated_amt  │      │
                    │    │ denied_amount    │      │
                    │    │ denial_reason    │      │
                    │    │ notes            │      │
                    │    └──────────────────┘      │
                    │                              │
                    │                              │
                    │    ┌──────────────────┐     │
                    │    │     providers    │◄────┘
                    │    ├──────────────────┤
                    │    │ provider_id(PK)  │
                    │    │ name             │
                    │    │ npi              │
                    │    │ specialty        │
                    │    │ address          │
                    │    │ phone            │
                    │    └──────────────────┘
                    │
                    │    ┌──────────────────┐
                    │    │     disputes     │
                    │    ├──────────────────┤
                    │    │ dispute_id (PK)  │
                    │    │ claim_id (FK)    │
                    │    │ member_id        │
                    │    │ line_item_ids    │
                    │    │ reason           │
                    │    │ status           │
                    │    │ created_at       │
                    │    │ resolved_at      │
                    │    └──────────────────┘
                    │
                    │    ┌──────────────────┐
                    │    │  usage_records   │
                    │    ├──────────────────┤
                    │    │ id (PK)          │
                    │    │ member_id (FK)   │
                    │    │ service_type     │
                    │    │ service_date     │
                    │    │ amount_paid      │
                    │    │ rule_id          │
                    │    │ created_at       │
                    │    └──────────────────┘
```

## Table Definitions

### members

Stores insurance policy members (covered individuals).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| member_id | VARCHAR(36) | PRIMARY KEY | Unique identifier (UUID) |
| first_name | VARCHAR(100) | NOT NULL | Member's first name |
| last_name | VARCHAR(100) | NOT NULL | Member's last name |
| date_of_birth | DATE | NOT NULL | Date of birth |
| email | VARCHAR(255) | NULLABLE | Email address |
| phone | VARCHAR(20) | NULLABLE | Phone number |
| created_at | DATETIME | NOT NULL | Record creation timestamp |

### policies

Insurance policies belonging to members.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| policy_id | VARCHAR(36) | PRIMARY KEY | Unique identifier (UUID) |
| member_id | VARCHAR(36) | FOREIGN KEY, UNIQUE | References members.member_id |
| policy_number | VARCHAR(50) | UNIQUE | Human-readable policy number |
| group_number | VARCHAR(50) | NULLABLE | Employer group number |
| policy_start | DATE | NOT NULL | Coverage start date |
| policy_end | DATE | NOT NULL | Coverage end date |
| created_at | DATETIME | NOT NULL | Record creation timestamp |
| updated_at | DATETIME | NOT NULL | Last update timestamp |

### coverage_rules

Coverage rules defining what services are covered under a policy.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| rule_id | VARCHAR(36) | PRIMARY KEY | Unique identifier (UUID) |
| policy_id | VARCHAR(36) | FOREIGN KEY | References policies.policy_id |
| service_type | ENUM | NOT NULL | Type of service covered |
| coverage_percentage | DECIMAL(5,4) | NOT NULL | Coverage ratio (0.0000-1.0000) |
| limit_type | ENUM | NOT NULL | Type of limit (annual, per_occurrence, etc.) |
| limit_amount | DECIMAL(12,2) | NOT NULL | Maximum covered amount |
| deductible_applies | BOOLEAN | DEFAULT FALSE | Whether deductible applies |
| deductible_amount | DECIMAL(12,2) | DEFAULT 0.00 | Deductible amount |
| effective_date | DATE | NOT NULL | Rule effective date |
| expiration_date | DATE | NULLABLE | Rule expiration date |

### claims

Insurance claims submitted by members.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| claim_id | VARCHAR(36) | PRIMARY KEY | Unique identifier (UUID) |
| member_id | VARCHAR(36) | FOREIGN KEY | References members.member_id |
| policy_id | VARCHAR(36) | FOREIGN KEY | References policies.policy_id |
| claim_number | VARCHAR(50) | UNIQUE | Human-readable claim number |
| status | ENUM | NOT NULL | Claim status (submitted, approved, etc.) |
| diagnosis_codes | TEXT | NULLABLE | JSON array of ICD-10 codes |
| accident_date | DATE | NULLABLE | Date of accident (if applicable) |
| accident_description | TEXT | NULLABLE | Accident description |
| total_requested | DECIMAL(12,2) | DEFAULT 0.00 | Total amount requested |
| total_approved | DECIMAL(12,2) | DEFAULT 0.00 | Total amount approved |
| total_denied | DECIMAL(12,2) | DEFAULT 0.00 | Total amount denied |
| created_at | DATETIME | NOT NULL | Record creation timestamp |
| submitted_at | DATETIME | NULLABLE | Submission timestamp |
| reviewed_at | DATETIME | NULLABLE | Review start timestamp |
| decided_at | DATETIME | NULLABLE | Decision timestamp |
| paid_at | DATETIME | NULLABLE | Payment timestamp |

### line_items

Individual expense items within a claim.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| line_item_id | VARCHAR(36) | PRIMARY KEY | Unique identifier (UUID) |
| claim_id | VARCHAR(36) | FOREIGN KEY | References claims.claim_id |
| provider_id | VARCHAR(36) | FOREIGN KEY, NULLABLE | References providers.provider_id |
| service_type | ENUM | NOT NULL | Type of service |
| service_date | DATE | NOT NULL | Date of service |
| description | TEXT | NOT NULL | Service description |
| amount | DECIMAL(12,2) | NOT NULL | Requested amount |
| diagnosis_codes | TEXT | NULLABLE | JSON array of ICD-10 codes |
| status | ENUM | NOT NULL | Line item status |
| adjudicated_amount | DECIMAL(12,2) | NULLABLE | Approved amount |
| denied_amount | DECIMAL(12,2) | NULLABLE | Denied amount |
| denial_reason | TEXT | NULLABLE | Reason for denial |
| notes | TEXT | NULLABLE | Additional notes |

### providers

Healthcare providers.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| provider_id | VARCHAR(36) | PRIMARY KEY | Unique identifier (UUID) |
| name | VARCHAR(200) | NOT NULL | Provider name |
| npi | VARCHAR(20) | NULLABLE | National Provider Identifier |
| specialty | VARCHAR(100) | NULLABLE | Medical specialty |
| address | TEXT | NULLABLE | Practice address |
| phone | VARCHAR(20) | NULLABLE | Contact phone |

### disputes

Member disputes of claim decisions.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| dispute_id | VARCHAR(36) | PRIMARY KEY | Unique identifier (UUID) |
| claim_id | VARCHAR(36) | FOREIGN KEY | References claims.claim_id |
| member_id | VARCHAR(36) | NOT NULL | Disputing member |
| line_item_ids | TEXT | NULLABLE | JSON array of disputed line item IDs |
| reason | TEXT | NOT NULL | Dispute reason |
| supporting_documents | TEXT | NULLABLE | JSON array of document references |
| status | ENUM | NOT NULL | Dispute status |
| created_at | DATETIME | NOT NULL | Record creation timestamp |
| reviewed_at | DATETIME | NULLABLE | Review timestamp |
| resolved_at | DATETIME | NULLABLE | Resolution timestamp |
| resolution_notes | TEXT | NULLABLE | Resolution notes |

### usage_records

Tracks member usage against coverage limits.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY, AUTOINCREMENT | Unique identifier |
| member_id | VARCHAR(36) | FOREIGN KEY | References members.member_id |
| service_type | ENUM | NOT NULL | Type of service |
| service_date | DATE | NOT NULL | Date of service |
| amount_paid | DECIMAL(12,2) | NOT NULL | Amount paid |
| rule_id | VARCHAR(36) | NOT NULL | Applied coverage rule ID |
| created_at | DATETIME | NOT NULL | Record creation timestamp |

## Enum Values

### ClaimStatus (claims.status)
- `submitted`
- `in_review`
- `approved`
- `partially_approved`
- `denied`
- `paid`
- `appeal`

### LineItemStatus (line_items.status)
- `pending`
- `approved`
- `denied`
- `needs_review`

### ServiceType (service_type fields)
- `primary_care`, `specialist`, `emergency`, `urgent_care`
- `inpatient`, `outpatient`, `surgery`
- `imaging`, `laboratory`, `physical_therapy`
- `prescription`, `mental_health`, `preventive`
- `cosmetic`, `other`

### CoverageLimitType (coverage_rules.limit_type)
- `per_occurrence`
- `per_visit`
- `annual_max`
- `per_calendar_year`
- `lifetime_max`

### DisputeStatus (disputes.status)
- `open`
- `under_review`
- `resolved`
- `overturned`
- `closed`

## Relationships

| Parent Table | Child Table | Relationship | Cardinality |
|--------------|-------------|--------------|-------------|
| members | policies | member has policy | 1:1 |
| members | claims | member submits claims | 1:* |
| members | usage_records | member has usage history | 1:* |
| policies | coverage_rules | policy contains rules | 1:* |
| policies | claims | policy covers claims | 1:* |
| claims | line_items | claim contains items | 1:* |
| claims | disputes | claim has disputes | 1:* |
| providers | line_items | provider renders service | 1:* |

## Indexes

Recommended indexes for production:

```sql
-- Members
CREATE INDEX idx_members_name ON members(last_name, first_name);

-- Policies
CREATE INDEX idx_policies_member ON policies(member_id);
CREATE INDEX idx_policies_number ON policies(policy_number);

-- Claims
CREATE INDEX idx_claims_member ON claims(member_id);
CREATE INDEX idx_claims_policy ON claims(policy_id);
CREATE INDEX idx_claims_status ON claims(status);
CREATE INDEX idx_claims_number ON claims(claim_number);
CREATE INDEX idx_claims_submitted ON claims(submitted_at);

-- Line Items
CREATE INDEX idx_line_items_claim ON line_items(claim_id);
CREATE INDEX idx_line_items_status ON line_items(status);

-- Coverage Rules
CREATE INDEX idx_coverage_rules_policy ON coverage_rules(policy_id);
CREATE INDEX idx_coverage_rules_service ON coverage_rules(service_type);

-- Disputes
CREATE INDEX idx_disputes_claim ON disputes(claim_id);
CREATE INDEX idx_disputes_status ON disputes(status);

-- Usage Records
CREATE INDEX idx_usage_member ON usage_records(member_id);
CREATE INDEX idx_usage_service_date ON usage_records(service_date);
CREATE INDEX idx_usage_member_year ON usage_records(member_id, service_date);
```

## Migrations

Database migrations can be managed with Alembic:

```bash
# Initialize Alembic
alembic init alembic

# Create a new migration
alembic revision --autogenerate -m "Initial schema"

# Apply migrations
alembic upgrade head
```

## Database Location

By default, SQLite database is stored at:
```
./claims.db
```

To change the location, modify `DATABASE_URL` in `app/database.py`.
