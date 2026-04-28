# Requirements and Assumptions Document

## Project Overview

**Assignment:** Forward Deployed Engineer - Take-Home Assignment (Level 1)  
**Task:** Build a Claims Processing System for an insurance company  
**Time Budget:** 1 day

---

## Core Requirements (From Assignment)

### Must-Have Functionality

1. **Claim Submission**
   - Claims can be submitted with multiple line items
   - Each line item has service type, date, amount, provider, diagnosis codes

2. **Coverage Rule Application**
   - System must apply coverage rules to determine payable amounts
   - Rules define what's covered, limits, deductibles, and percentages

3. **Claim Lifecycle States**
   - Claims move through states: submitted → under review → approved/denied → paid

4. **Decision Explanations**
   - System must explain why claims/line items were approved or denied

### Required Deliverables

| Deliverable | Status | Location |
|-------------|--------|----------|
| Working system | ✅ Complete | `app/` |
| Domain model doc | ✅ Complete | `docs/domain-model.md` |
| Decisions doc | ✅ Complete | `docs/decisions.md` |
| Self-review | ✅ Complete | `docs/self-review.md` |
| AI artifacts | ✅ This folder | `ai-artifacts/` |
| README.md | ✅ Complete | `README.md` |

---

## Assumptions Made

### Domain Assumptions

#### 1. One Policy Per Member
**Assumption:** Each member has exactly one policy.  
**Rationale:** Simplifies the domain model for this exercise.  
**Real-world gap:** Actual systems support multiple policies, coordination of benefits, and policy changes over time.  
**Extension point:** Add `PolicyMember` junction table with effective dates and priority ordering.

#### 2. Service Date Determines Applicable Rules
**Assumption:** Coverage rules active on the service date apply, not the submission date.  
**Rationale:** Standard industry practice - coverage is based on when service was rendered.  
**Implication:** Retroactive policy changes don't affect already-rendered services.

#### 3. Claims Are Immutable After Submission
**Assumption:** Once submitted, claims cannot be modified (only adjudicated).  
**Rationale:** Simplifies state management and audit trail.  
**Real-world gap:** Actual systems support claim adjustments, corrections, and reprocessing.  
**Extension point:** Add claim versioning or adjustment line items with reference to original.

#### 4. Calendar Year Reset for Annual Limits
**Assumption:** Annual limits reset on January 1st.  
**Rationale:** Most common plan year structure.  
**Real-world gap:** Some plans use anniversary year (from enrollment date) or fiscal year.  
**Extension point:** Add `plan_year_type` field to Policy with configurable start month.

#### 5. Line Items Are Adjudicated Independently
**Assumption:** Each line item is evaluated separately without bundling rules.  
**Rationale:** Keeps adjudication logic simple and testable.  
**Real-world gap:** Actual systems have CPT code bundling, NCCI edits, and procedure combinations.  
**Extension point:** Add `BundlingRule` entity with parent/child procedure relationships.

#### 6. No Provider Network Differentiation
**Assumption:** All providers are treated equally; no in-network vs out-of-network.  
**Rationale:** Would double the coverage rule complexity.  
**Real-world gap:** Network status significantly affects coverage levels.  
**Extension point:** Add `network_status` to Provider and `in_network_pct` / `out_network_pct` to CoverageRule.

#### 7. Deductible Tracking Is Simplified
**Assumption:** Deductibles are tracked per-claim, not accumulated across all claims.  
**Rationale:** Cross-claim deductible tracking requires additional infrastructure.  
**Real-world gap:** Deductibles should accumulate across all claims in a plan year.  
**Extension point:** Add `DeductibleTracker` service that queries all claims for the member.

#### 8. No Prior Authorization Requirement
**Assumption:** Services don't require pre-approval before being rendered.  
**Rationale:** Adds workflow complexity beyond core adjudication.  
**Real-world gap:** Many procedures require prior auth for coverage.  
**Extension point:** Add `Authorization` entity with required/procedure mappings.

#### 9. Simple Dispute Workflow
**Assumption:** Disputes are tracked but don't have a full workflow engine.  
**Rationale:** Core assignment is about adjudication, not appeals management.  
**Real-world gap:** Full appeals process with timelines, external review, etc.  
**Extension point:** Add `DisputeWorkflow` with state machine and SLA tracking.

#### 10. Single Currency (USD)
**Assumption:** All amounts are in US dollars.  
**Rationale:** Assignment context is US insurance.  
**Extension point:** Add `Currency` value object with conversion logic.

---

## Technical Assumptions

### 1. Python 3.11+
**Assumption:** Modern Python with type hints and dataclasses.  
**Rationale:** Best developer experience, strong typing for domain models.

### 2. SQLite for Persistence
**Assumption:** SQLite is sufficient for demonstration purposes.  
**Rationale:** No setup required, file-based, easy to share.  
**Trade-off:** Not suitable for production scale; would need PostgreSQL.

### 3. FastAPI for API Layer
**Assumption:** RESTful API with automatic documentation.  
**Rationale:** Rapid development, Pydantic integration, Swagger UI included.

### 4. In-Memory → Database Architecture
**Assumption:** Repository pattern allows swapping implementations.  
**Rationale:** Started with in-memory for speed, added SQLAlchemy for persistence.

### 5. Decimal for Monetary Values
**Assumption:** Using `Decimal` instead of `float` for money.  
**Rationale:** Avoids floating-point precision errors in financial calculations.

### 6. No Authentication/Authorization
**Assumption:** API is open without auth for demonstration.  
**Rationale:** Auth is orthogonal to domain modeling exercise.  
**Production need:** Add JWT/OAuth2 middleware.

### 7. No Frontend UI
**Assumption:** API + Swagger UI is sufficient for demonstration.  
**Rationale:** Backend domain modeling is the core challenge.  
**Extension:** Could add Streamlit/React frontend for visual demo.

---

## Design Decisions

### What Was Built vs What Was Skipped

| Built | Skipped | Reason |
|-------|---------|--------|
| Core adjudication engine | Deductible accumulation | Time budget; pattern demonstrated |
| Coverage rule application | Prior authorization | Out of scope for adjudication focus |
| Claim lifecycle states | Claim adjustments | Immutability simplifies model |
| Explanation generation | Full denial letter workflow | Basic explanation sufficient |
| Dispute tracking | Appeals workflow | Core is adjudication |
| Usage tracking | Cross-member family limits | Added complexity |
| In-memory + DB repos | Event sourcing | Over-engineering for scope |
| Unit tests | Integration tests | Core logic tested |

---

## Edge Cases Handled

| Edge Case | How Handled |
|-----------|-------------|
| No coverage rule for service type | Denied with clear reason |
| Annual limit exhausted | Denied with explanation of used amount |
| Partial limit remaining | Payment capped at remaining limit |
| Mixed line items (some covered, some not) | Partial approval status |
| High-dollar claims | Flagged for manual review (>$10,000) |
| Large denials | Flagged for review (>$1,000) |
| Calendar year boundary | Usage only counts within same year |

---

## Edge Cases NOT Handled

| Edge Case | Why Not Handled |
|-----------|-----------------|
| Overlapping coverage rules | Would require rule priority system |
| Coordination of benefits (multiple policies) | Complex domain beyond scope |
| Retroactive policy changes | Snapshot at service time |
| Claim adjustments after payment | Requires versioning |
| Dependent coverage under family policy | One member per policy assumption |
| Provider network tiers | Single network assumption |
| Cumulative deductible tracking | Per-claim deductible only |

---

## API Endpoints Implemented

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/members` | Create member |
| GET | `/api/v1/members/{id}` | Get member |
| GET | `/api/v1/members` | List all members |
| POST | `/api/v1/policies` | Create policy with rules |
| GET | `/api/v1/policies/{id}` | Get policy |
| GET | `/api/v1/members/{id}/policy` | Get member's policy |
| POST | `/api/v1/claims` | Submit claim (auto-adjudicated) |
| GET | `/api/v1/claims/{id}` | Get claim |
| GET | `/api/v1/claims/{id}/adjudication` | Get adjudication results |
| GET | `/api/v1/claims/{id}/explanation` | Get human-readable explanation |
| GET | `/api/v1/members/{id}/claims` | List member's claims |
| POST | `/api/v1/claims/{id}/disputes` | File dispute |
| GET | `/api/v1/claims/{id}/disputes` | List claim disputes |
| GET | `/api/v1/disputes/{id}` | Get dispute |

---

## Coverage Rules Implemented

| Plan | Service Type | Coverage % | Annual Limit | Deductible |
|------|-------------|------------|--------------|------------|
| Gold | Preventive | 100% | $2,000 | No |
| Gold | Primary Care | 90% | $5,000 | $250 |
| Gold | Specialist | 80% | $10,000 | $250 |
| Gold | Laboratory | 100% | $3,000 | No |
| Gold | Physical Therapy | 70% | $2,000 | No |
| Gold | Emergency | 90% | $50,000 | $500 |
| Silver | Preventive | 100% | $1,000 | No |
| Silver | Primary Care | 70% | $3,000 | $500 |
| Silver | Specialist | 60% | $6,000 | $500 |
| Silver | Laboratory | 80% | $2,000 | No |
| Silver | Emergency | 70% | $30,000 | $1,000 |
| Bronze | Preventive | 80% | $500 | No |
| Bronze | Primary Care | 50% | $2,000 | $1,000 |
| Bronze | Emergency | 50% | $20,000 | $2,000 |
| Platinum | Preventive | 100% | $5,000 | No |
| Platinum | Primary Care | 100% | $10,000 | No |
| Platinum | Specialist | 95% | $20,000 | No |
| Platinum | Surgery | 90% | $100,000 | No |
| Platinum | Mental Health | 90% | $10,000 | No |

---

## Test Coverage

| Component | Tests | Status |
|-----------|-------|--------|
| Adjudication Engine | 11 tests | ✅ Passing |
| Coverage Tracker | 2 tests | ✅ Passing |
| Explanation Generator | 7 tests | ✅ Passing |
| **Total** | **19 tests** | **✅ All Passing** |

---

## Known Limitations (Production Readiness)

### Must Fix Before Production

1. **Deductible tracking** - Not accumulated across claims
2. **Claim validation** - Missing input validation
3. **Usage recording timing** - Should be at payment, not adjudication
4. **Logging/auditing** - No audit trail
5. **Database persistence** - Currently SQLite; need PostgreSQL

### Should Fix

1. **Pagination** - List endpoints return all records
2. **Error handling** - Minimal exception handling
3. **Integration tests** - API-level testing

### Nice to Have

1. **Provider network rules** - In/out of network
2. **Family policies** - Dependents under primary member
3. **Prior authorization** - Pre-approval workflow
4. **Claims adjustment** - Modify submitted claims

---

## Conclusion

This implementation demonstrates:

- ✅ Clean domain decomposition
- ✅ Testable architecture
- ✅ Explainable decisions
- ✅ Awareness of trade-offs

The gaps are documented and fixable. The core model is sound for extending with appeals workflow or eligibility verification as mentioned in the assignment.
