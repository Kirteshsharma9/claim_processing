# Decisions & Trade-offs

## What Was Built

### Core System

1. **Domain Model** (`app/domain/`)
   - Complete entity model with Member, Policy, CoverageRule, Claim, LineItem
   - Value objects for Money (Decimal precision), DateRange, PolicyPeriod
   - Enums for all state machines (ClaimStatus, LineItemStatus, ServiceType, etc.)

2. **Adjudication Engine** (`app/services/adjudication.py`)
   - Rule matching by service type and date
   - Coverage percentage calculation
   - Limit exhaustion checking
   - Manual review flagging for high-dollar/large-denial claims

3. **Coverage Tracker** (`app/services/coverage.py`)
   - Usage history tracking
   - Calendar year boundary handling
   - Multiple limit types (per-occurrence, annual, lifetime)

4. **Explanation Generator** (`app/services/explanation.py`)
   - Line-item explanations
   - Claim summaries
   - Formal denial letters

5. **Repository Layer** (`app/repositories/in_memory.py`)
   - In-memory implementation for all entities
   - Unit of Work pattern for transactional operations
   - Easy to swap for database-backed implementation

6. **API Layer** (`app/api/routes.py`)
   - RESTful endpoints for Members, Policies, Claims, Disputes
   - Automatic claim adjudication on submission
   - Explanation endpoints for human-readable decisions

7. **Unit Tests** (`app/tests/`)
   - Adjudication engine tests (rule matching, limits, partial approvals)
   - Explanation generator tests

---

## What Was NOT Built

### 1. Database Persistence

**Decision:** Used in-memory repositories instead of SQLite/database.

**Why:**
- Faster to develop and demonstrate
- No migration/setup complexity
- Sufficient for assignment demonstration
- Repository pattern makes it swappable

**Trade-off:** Data lost on restart. For production, would implement SQLAlchemy repositories.

### 2. Authentication/Authorization

**Decision:** No auth layer.

**Why:**
- Out of scope for domain modeling exercise
- Would add complexity without demonstrating domain thinking

**Trade-off:** API is completely open. Would add JWT/auth in production.

### 3. Frontend/UI

**Decision:** API-only with Swagger UI for interaction.

**Why:**
- Backend domain modeling is the core challenge
- Swagger UI provides adequate interaction for demo
- Frontend would distract from domain concerns

**Trade-off:** Less polished demo. Could add simple Streamlit/React frontend if needed.

### 4. Comprehensive Edge Cases

**Decision:** Implemented core edge cases but not all possible scenarios.

**What's handled:**
- Limit exhaustion
- Partial approvals
- Calendar year boundaries
- High-dollar review flags

**What's NOT handled:**
- Overlapping coverage rules (multiple rules for same service)
- Coordination of benefits (multiple policies)
- Dependent coverage under family policies
- Retroactive policy changes mid-claim
- Claim adjustments/corrections after payment

**Why:** Time budget of 1 day. Focused on demonstrating coherent domain model over feature completeness.

### 5. Deductible Tracking

**Decision:** Deductible logic is simplified.

**What's there:** CoverageRule has `deductible_applies` and `deductible_amount` fields.

**What's missing:** Cross-claim deductible tracking (how much deductible has been met across all claims).

**Why:** Would require additional infrastructure (deductible tracking service, cross-claim aggregation). Core coverage logic demonstrates the pattern adequately.

### 6. Provider Network Rules

**Decision:** Provider is informational only.

**What's missing:** In-network vs out-of-network differentiation, network-based coverage levels.

**Why:** Would double the complexity of coverage rules (separate rules for in/out network). Can be added as a `Provider.network_status` field and rule matching extension.

---

## Assumptions Made

### Domain Assumptions

1. **One Policy Per Member**
   - Simplified model. Real systems support multiple policies, coordination of benefits.
   - Extension: Add `PolicyMember` junction table with priority ordering.

2. **Service Date Determines Applicable Rules**
   - Coverage rules active on service date apply, not submission date.
   - This is standard industry practice.

3. **Claims Are Not Modified After Submission**
   - Immutability assumption. Real systems support claim adjustments.
   - Extension: Add claim versioning or adjustment line items.

4. **Usage Resets on Calendar Year**
   - January 1 reset for annual limits.
   - Some plans use anniversary year (from enrollment date). Extension point in `CoverageTracker._get_period_bounds()`.

5. **Line Items Are Independent**
   - Each line item adjudicated separately.
   - Real systems may have bundling rules (certain services always together).

### Technical Assumptions

1. **Python 3.11+**
   - Used modern Python features (type hints, dataclasses)

2. **FastAPI for API Layer**
   - Chosen for rapid development, auto-docs, Pydantic integration

3. **Decimal for Money**
   - Avoids floating-point precision issues
   - Standard practice for financial calculations

4. **In-Memory Storage**
   - Acceptable for demo/development
   - Repository pattern enables database swap

---

## Architecture Decisions

### 1. Dataclasses Over Pydantic for Domain Models

**Decision:** Used `@dataclass` for domain entities, not Pydantic models.

**Why:**
- Domain models are business logic, not API boundaries
- Dataclasses are lighter weight
- Pydantic used only at API boundary (request/response models)

**Trade-off:** Two model types to maintain, but cleaner separation of concerns.

### 2. Service Layer Pattern

**Decision:** Business logic in `services/` module, not in domain models.

**Why:**
- Domain models are anemic data structures
- Services are testable in isolation
- Clear separation: domain = what, services = how

**Trade-off:** More files, but easier to test and reason about.

### 3. Repository Pattern

**Decision:** Abstracted data access behind repository interfaces.

**Why:**
- Easy to swap in-memory for database
- Testable without database dependencies
- Follows DDD patterns

**Trade-off:** Slightly more boilerplate, but worth it for flexibility.

### 4. Derived Claim Status

**Decision:** Claim status computed from line item statuses, not stored independently.

**Why:**
- Single source of truth
- No risk of status desynchronization
- Clearer business rules

**Trade-off:** Must compute on read, but computation is trivial.

---

## Alternative Approaches Considered

### 1. Coverage Rules as DSL/Config

**Considered:** YAML/JSON configuration for coverage rules.

**Rejected because:**
- Code-based rules are more flexible
- Easier to test
- Can express complex logic (date ranges, conditionals)

**When to use config:** If business users need to modify rules without code changes.

### 2. Event Sourcing for Claims

**Considered:** Store claim events (Submitted, Adjudicated, Paid) and derive state.

**Rejected because:**
- Over-engineering for this scope
- Adds significant complexity
- CRUD is sufficient for demonstration

**When to use event sourcing:** Audit requirements, temporal queries, complex undo/redo.

### 3. Database-First Design

**Considered:** Design schema first, then code.

**Rejected because:**
- Domain-driven design prioritizes business logic over persistence
- In-memory is faster for iteration
- Schema can be derived from domain models later

---

## Future Extension Points

### 1. Family Policies

Add `FamilyMember` entity with relationship to primary member. Coverage rules would apply to family unit with individual and family limits.

### 2. Prior Authorization

Add `Authorization` entity for services requiring pre-approval. Claims would check for required authorizations before adjudication.

### 3. Appeals Workflow

Extend `Dispute` with full workflow: submission, review, decision, external review. Currently only tracks dispute existence.

### 4. Claims History Analytics

Usage tracking infrastructure could support analytics: trend analysis, fraud detection, cost prediction.

### 5. Rule Engine Enhancement

Replace hardcoded adjudication logic with rules engine (Drools, EasyRules) for business-user-configurable rules.

---

## Summary

This implementation prioritizes:

1. **Clear domain modeling** over feature completeness
2. **Testability** over convenience
3. **Explainability** over automation
4. **Extensibility** over optimization

The system demonstrates coherent abstractions that can be explained, modified, and extended. Trade-offs are documented and can be revisited based on production requirements.
