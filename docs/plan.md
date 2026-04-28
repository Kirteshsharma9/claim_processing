# Claims Processing System - Implementation Plan

## Context

This is a Forward Deployed Engineer take-home assignment (Level 1). The goal is to build a Claims Processing System that demonstrates domain modeling skills, not just CRUD functionality. The system must process insurance claims with coverage rules, handle partial approvals, track claim lifecycle, and explain decisions.

**Time budget:** 1 day
**Key evaluation criteria:** Domain decomposition, rule representation, state management, edge case handling, explanation capability

---

## Recommended Approach

### Technology Stack

**Python with FastAPI** - Recommended for:
- Rapid development with clear, readable code
- Automatic API documentation (Swagger UI)
- Easy testing with pytest
- Strong typing with Pydantic for domain models

**SQLite** for persistence - Simple, file-based, no setup required, sufficient for demonstration

**No frontend** - CLI + API endpoints with JSON responses. Build something that can be demoed via curl/Postman.

---

## Domain Model

### Core Entities

```
Member
  └── Policy
        ├── CoverageRule (multiple)
        └── Claim (multiple)
              ├── LineItem (multiple)
              └── AdjudicationResult (per line item)
```

### Key Abstractions

1. **CoverageRule** - Represents what's covered
   - Service type (e.g., "physical_therapy", "x_ray")
   - Limit type (per_occurrence, annual_max, per_visit)
   - Amount/percentage covered
   - Deductible applicability

2. **Claim** - The aggregate root
   - States: SUBMITTED → IN_REVIEW → APPROVED/PARTIALLY_APPROVED/DENIED → PAID
   - Contains member info, diagnosis codes, provider details
   - Has multiple line items

3. **LineItem** - Individual expense within a claim
   - Service type, date, amount, provider
   - Its own adjudication state (can differ from claim state)

4. **AdjudicationEngine** - Pure function that applies rules
   - Input: LineItem + CoverageRules + UsageHistory
   - Output: PayableAmount + Reason + RemainingLimits

5. **ExplanationGenerator** - Builds human-readable denial/approval reasons

---

## Architecture

```
app/
├── main.py              # FastAPI entry point, routes
├── domain/
│   ├── models.py        # Pydantic models (Member, Policy, Claim, LineItem)
│   ├── enums.py         # ClaimStatus, CoverageType, etc.
│   └── value_objects.py # Money, ServiceType, DateRange
├── services/
│   ├── adjudication.py  # Core rule engine
│   ├── coverage.py      # Coverage rule evaluation
│   └── explanation.py   # Generate human-readable reasons
├── repositories/
│   └── in_memory.py     # Simple storage (can swap for DB later)
├── api/
│   └── routes.py        # HTTP endpoints
└── tests/
    ├── test_adjudication.py
    └── test_coverage.py

docs/
├── domain-model.md
├── decisions.md
└── self-review.md

ai-artifacts/            # Chat exports
```

---

## Coverage Rule Design

Use a **code-based strategy pattern** rather than config/DSL for flexibility:

```python
class CoverageRule:
    service_type: ServiceType
    limit: CoverageLimit  # e.g., AnnualMax(5000), PerVisit(200)
    coverage_pct: float   # e.g., 0.8 = 80% covered
    deductible_applies: bool

class AdjudicationEngine:
    def adjudicate(self, line_item, rules, usage_history) -> AdjudicationResult:
        rule = find_applicable_rule(line_item.service_type, rules)
        if not rule:
            return denied("No coverage for this service type")

        remaining = rule.limit.remaining(usage_history)
        payable = min(line_item.amount * rule.coverage_pct, remaining)

        return AdjudicationResult(
            payable=payable,
            denied_amount=line_item.amount - payable,
            reason=build_explanation(rule, payable, remaining)
        )
```

---

## State Machine

**Claim Level:**
```
SUBMITTED → IN_REVIEW → {APPROVED, PARTIALLY_APPROVED, DENIED} → PAID
                         ↑
                    (can transition to APPEAL if disputed)
```

**Line Item Level:**
```
PENDING → {APPROVED, DENIED, NEEDS_REVIEW}
```

Claim status is derived from line item statuses:
- All APPROVED → CLAIM APPROVED
- All DENIED → CLAIM DENIED
- Mixed → CLAIM PARTIALLY_APPROVED

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /members | Create member with policy |
| GET | /members/{id} | Get member details |
| POST | /claims | Submit new claim |
| GET | /claims/{id} | Get claim status + results |
| GET | /claims/{id}/explanation | Get denial/approval explanation |
| POST | /claims/{id}/dispute | Initiate dispute on claim |

---

## Implementation Phases

### Phase 1: Core Domain (2-3 hours)
- Define Pydantic models (Member, Policy, Claim, LineItem)
- Implement enums (ClaimStatus, ServiceType)
- Build CoverageRule and CoverageLimit classes
- Create in-memory repository

### Phase 2: Adjudication Engine (2-3 hours)
- Implement rule matching logic
- Build limit tracking (annual, per-occurrence)
- Create adjudication function
- Handle partial approvals

### Phase 3: API Layer (1-2 hours)
- FastAPI setup
- POST /claims endpoint with auto-adjudication
- GET endpoints for retrieval
- Explanation endpoint

### Phase 4: Documentation (1 hour)
- docs/domain-model.md - Entity diagrams, state machines
- docs/decisions.md - What was built, what wasn't, why
- docs/self-review.md - Honest assessment

### Phase 5: AI Artifacts + Polish (1 hour)
- Export chat sessions
- Write README.md
- Final test pass

---

## Edge Cases to Handle

1. **Limit exhaustion** - Claim submitted after annual max reached
2. **Partial approval** - 5 line items, 3 covered, 2 denied
3. **Retroactive changes** - What if policy is updated after claim submitted? (Snapshot policy at claim time)
4. **Overlapping coverage** - Multiple rules for same service (use most specific, or sum?)
5. **Zero-amount claims** - Edge case testing

---

## Files to Create

**Application:**
- `app/main.py`
- `app/domain/models.py`
- `app/domain/enums.py`
- `app/domain/value_objects.py`
- `app/services/adjudication.py`
- `app/services/coverage.py`
- `app/services/explanation.py`
- `app/repositories/in_memory.py`
- `app/api/routes.py`
- `app/tests/test_adjudication.py`

**Documentation:**
- `docs/domain-model.md`
- `docs/decisions.md`
- `docs/self-review.md`
- `README.md`
- `ai-artifacts/` (chat exports)

---

## Verification

1. Run: `python -m uvicorn app.main:app --reload`
2. Test claim submission via POST /claims
3. Verify adjudication results in response
4. Check explanation endpoint returns readable text
5. Run pytest for unit tests
