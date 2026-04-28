# Domain Model

## Overview

This Claims Processing System models the core entities and workflows of insurance claim adjudication. The domain is decomposed to clearly separate:

1. **Who** - Members and Providers
2. **What** - Policies, Coverage Rules, Claims, Line Items
3. **How** - Adjudication Engine, Coverage Tracker
4. **Why** - Explanation Generator for decision transparency

---

## Core Entities

### Member

A person covered by an insurance policy.

```
Member
├── member_id: str (unique identifier)
├── first_name: str
├── last_name: str
├── date_of_birth: date
├── email: str (optional)
├── phone: str (optional)
└── created_at: datetime
```

### Policy

An insurance policy belonging to a member, containing coverage rules.

```
Policy
├── policy_id: str
├── member_id: str (foreign key)
├── policy_number: str (human-readable)
├── group_number: str (optional, for employer groups)
├── period: PolicyPeriod (start/end dates)
├── coverage_rules: list[CoverageRule]
└── created_at, updated_at: datetime
```

### CoverageRule

Defines what services are covered and under what terms.

```
CoverageRule
├── rule_id: str
├── service_type: ServiceType (enum)
├── coverage_percentage: Decimal (0.80 = 80%)
├── limit_type: CoverageLimitType (enum)
├── limit_amount: Money
├── deductible_applies: bool
├── deductible_amount: Money
├── effective_date: date
└── expiration_date: date (optional)
```

**Limit Types:**
- `PER_OCCURRENCE` - Reset after each claim
- `PER_VISIT` - Same as per_occurrence
- `ANNUAL_MAX` - Resets each calendar year
- `PER_CALENDAR_YEAR` - Same as annual_max
- `LIFETIME_MAX` - Never resets

### Claim

The aggregate root representing a submitted claim for reimbursement.

```
Claim
├── claim_id: str
├── member_id: str
├── policy_id: str
├── claim_number: str (human-readable)
├── line_items: list[LineItem]
├── diagnosis_codes: list[str] (ICD-10)
├── accident_date: date (optional)
├── accident_description: str (optional)
├── status: ClaimStatus (derived)
├── total_requested: Money
├── total_approved: Money
├── total_denied: Money
└── timestamps: created, submitted, reviewed, decided, paid
```

### LineItem

An individual expense within a claim, adjudicated independently.

```
LineItem
├── line_item_id: str
├── service_type: ServiceType
├── service_date: date
├── description: str
├── amount: Money
├── provider: Provider (optional)
├── diagnosis_codes: list[str]
├── status: LineItemStatus
├── adjudicated_amount: Money
├── denied_amount: Money
└── denial_reason: str (optional)
```

### Provider

Healthcare provider information.

```
Provider
├── provider_id: str
├── name: str
├── npi: str (National Provider Identifier)
├── specialty: str
├── address: str
└── phone: str
```

### Dispute

Member dispute of a claim decision.

```
Dispute
├── dispute_id: str
├── claim_id: str
├── member_id: str
├── line_item_ids: list[str]
├── reason: str
├── supporting_documents: list[str]
├── status: DisputeStatus
└── timestamps: created, reviewed, resolved
```

---

## Value Objects

### Money

Immutable monetary value using `Decimal` for precision.

```python
@dataclass(frozen=True)
class Money:
    amount: Decimal  # Always 2 decimal places
```

### DateRange

Immutable date range for policy periods and coverage windows.

```python
@dataclass(frozen=True)
class DateRange:
    start: date
    end: Optional[date]
```

### PolicyPeriod

Policy coverage period with validation.

```python
@dataclass(frozen=True)
class PolicyPeriod:
    start: date
    end: date  # Must be after start
```

---

## Enums

### ClaimStatus

```
SUBMITTED → IN_REVIEW → {APPROVED, PARTIALLY_APPROVED, DENIED} → PAID
                           ↑
                      (APPEAL if disputed)
```

### LineItemStatus

```
PENDING → {APPROVED, DENIED, NEEDS_REVIEW}
```

### ServiceType

```
PRIMARY_CARE, SPECIALIST, EMERGENCY, URGENT_CARE,
INPATIENT, OUTPATIENT, SURGERY, IMAGING, LABORATORY,
PHYSICAL_THERAPY, PRESCRIPTION, MENTAL_HEALTH,
PREVENTIVE, COSMETIC, OTHER
```

### CoverageLimitType

```
PER_OCCURRENCE, PER_VISIT, ANNUAL_MAX,
PER_CALENDAR_YEAR, LIFETIME_MAX
```

### DisputeStatus

```
OPEN → UNDER_REVIEW → {RESOLVED, OVERTURNED, CLOSED}
```

---

## State Machines

### Claim Lifecycle

```
                    ┌─────────────┐
                    │  SUBMITTED  │
                    └──────┬──────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  IN_REVIEW  │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌──────────┐  ┌─────────────────┐  ┌─────────┐
    │ APPROVED │  │PARTIALLY_APPROVED│  │ DENIED  │
    └────┬─────┘  └────────┬────────┘  └────┬────┘
         │                 │                │
         └─────────────────┼────────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │    PAID     │
                    └─────────────┘
```

**Status Derivation:**
- All line items `APPROVED` → Claim `APPROVED`
- All line items `DENIED` → Claim `DENIED`
- Mixed statuses → Claim `PARTIALLY_APPROVED`
- Any item `NEEDS_REVIEW` → Claim `IN_REVIEW`
- Dispute filed → Claim `APPEAL`

### LineItem Adjudication Flow

```
┌─────────┐     ┌─────────────────────┐     ┌──────────────┐
│ PENDING │────▶│  AdjudicationEngine │────▶│   APPROVED   │
└─────────┘     └─────────────────────┘     └──────────────┘
                         │                   ┌──────────────┐
                         │                   │    DENIED    │
                         │                   └──────────────┘
                         │                   ┌──────────────┐
                         └──────────────────▶│ NEEDS_REVIEW │
                                             └──────────────┘
```

---

## Services

### AdjudicationEngine

Pure function that applies coverage rules to line items.

**Responsibilities:**
1. Find applicable coverage rule for service type
2. Check if limit is exhausted
3. Calculate payable amount (coverage % × amount, capped by limit)
4. Apply deductible if applicable
5. Flag for manual review if high-dollar or large denial

**Input:**
- `LineItem`
- `Policy` (with coverage rules)
- `UsageHistory` (prior claims for limit tracking)

**Output:**
- `AdjudicationResult` (payable, denied, reason, requires_review)

### CoverageTracker

Tracks member's usage of covered services.

**Responsibilities:**
1. Calculate remaining limit for a service type
2. Determine period bounds (calendar year, lifetime, etc.)
3. Check if limit is exhausted

### ExplanationGenerator

Generates human-readable explanations for decisions.

**Responsibilities:**
1. Generate line-item level explanations
2. Generate claim-level summaries
3. Generate formal denial letters

---

## Relationships

```
Member (1) ──────< Policy (1)
                         │
                         │ contains
                         ▼
                  CoverageRule (*)
                         │
                         │ applied to
                         ▼
Member (1) ──────< Claim (*) ──────> LineItem (*)
                         │
                         │ disputed by
                         ▼
                   Dispute (*)
```

---

## Key Design Decisions

### 1. Claim Status is Derived

Claim status is not stored independently but derived from line item statuses. This ensures consistency and eliminates the need to manage two separate state machines.

### 2. Policy Snapshot at Claim Time

When a claim is submitted, the applicable coverage rules are those active on the service date. This handles retroactive policy changes cleanly.

### 3. LineItem-Level Adjudication

Each line item is adjudicated independently, allowing for partial approvals within a single claim. This is more realistic than all-or-nothing claim decisions.

### 4. Usage Tracking Separate from Rules

Usage history is tracked separately from coverage rules, making it easy to calculate remaining limits without modifying the rule definitions.

### 5. Explanation as First-Class Concern

The `ExplanationGenerator` is a dedicated service, not an afterthought. This ensures decisions are always accompanied by clear, auditable reasoning.
