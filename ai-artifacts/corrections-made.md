# AI Corrections Log

This document tracks specific instances where AI-generated code was incorrect and required human correction.

---

## Critical Corrections

### 1. Adjudication Engine: Missing Limit Check

**AI's Original Code:**
```python
def adjudicate(self, line_item, rules, usage_history):
    rule = find_applicable_rule(line_item.service_type, rules)
    if not rule:
        return denied("No coverage rule found")
    
    # Calculate payable amount
    payable = line_item.amount * rule.coverage_percentage
    
    return AdjudicationResult(payable=paidable, denied=Money.zero())
```

**Problem:** No check for whether the member has exhausted their annual limit.

**My Correction:**
```python
def adjudicate(self, line_item, rules, usage_history):
    rule = find_applicable_rule(line_item.service_type, rules)
    if not rule:
        return denied("No coverage rule found")
    
    # NEW: Check if limit is exhausted
    tracker = CoverageTracker(usage_history)
    if tracker.is_limit_exhausted(line_item.service_type, rule, line_item.service_date):
        return denied(f"Limit exhausted for {line_item.service_type.value}")
    
    # NEW: Cap by remaining limit
    remaining = tracker.get_available_amount(line_item.service_type, rule, line_item.service_date)
    payable = min(line_item.amount * rule.coverage_percentage, remaining)
    
    return AdjudicationResult(payable=paidable, denied=...)
```

**Impact:** Without this fix, members could receive unlimited payments even after hitting their annual max.

---

### 2. Deductible Calculation Order

**AI's Original Code:**
```python
# Apply coinsurance first
payable = line_item.amount * rule.coverage_percentage

# Then subtract deductible
if rule.deductible_applies:
    payable = payable - rule.deductible_amount
```

**Problem:** Deductibles are applied BEFORE coinsurance in real insurance. Member pays the full deductible amount first, then coinsurance applies to the remainder.

**My Correction:**
```python
amount = line_item.amount

# Apply deductible FIRST
if rule.deductible_applies:
    deductible_remaining = get_deductible_remaining(member_id)
    amount_after_deductible = max(0, amount - deductible_remaining)
    # Coinsurance applies to amount after deductible
    payable = amount_after_deductible * rule.coverage_percentage
else:
    payable = amount * rule.coverage_percentage
```

**Impact:** Wrong calculation would underpay claims significantly.

---

### 3. Claim Status: Independent vs Derived

**AI's Suggestion:**
```python
class Claim:
    status: ClaimStatus  # Stored field
    
    def update_status(self, new_status):
        self.status = new_status
```

**Problem:** Claim status should be DERIVED from line item statuses, not stored independently. This prevents state desynchronization.

**My Correction:**
```python
class Claim:
    status: ClaimStatus  # Still stored for convenience, but derived
    
    def derive_status(self) -> ClaimStatus:
        """Derive claim status from line item statuses."""
        if not self.line_items:
            return ClaimStatus.SUBMITTED
        
        adjudicated = [item for item in self.line_items if item.is_adjudicated()]
        if not adjudicated:
            return ClaimStatus.SUBMITTED
        
        statuses = {item.status for item in adjudicated}
        
        if LineItemStatus.NEEDS_REVIEW in statuses:
            return ClaimStatus.IN_REVIEW
        
        if len(statuses) == 1:
            if LineItemStatus.APPROVED in statuses:
                return ClaimStatus.APPROVED
            elif LineItemStatus.DENIED in statuses:
                return ClaimStatus.DENIED
        
        # Mixed statuses
        if LineItemStatus.APPROVED in statuses and LineItemStatus.DENIED in statuses:
            return ClaimStatus.PARTIALLY_APPROVED
        
        return self.status
    
    def adjudicate_all(self, results):
        """Adjudicate all items and update status."""
        # ... apply results to line items ...
        self._recalculate_totals()
        self.update_status(self.derive_status())  # Derive, don't set manually
```

**Impact:** Prevents bugs where claim status doesn't match line item statuses.

---

### 4. Provider Model: Missing Relationship

**AI's Generated Code:**
```python
class ProviderModel(Base):
    __tablename__ = "providers"
    
    provider_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # ... other fields but NO relationships
```

**Problem:** LineItemModel has `back_populates="provider"` but ProviderModel doesn't define the relationship.

**Error:**
```
sqlalchemy.exc.InvalidRequestError: Mapper 'Mapper[ProviderModel(providers)]' 
has no property 'line_items'.
```

**My Correction:**
```python
class ProviderModel(Base):
    # ... existing fields ...
    
    # ADDED: Missing relationship
    line_items: Mapped[List["LineItemModel"]] = relationship(
        "LineItemModel", back_populates="provider"
    )
```

**Impact:** Database seeder failed completely without this fix.

---

### 5. Money Fields: Float vs Decimal

**AI's Generated Code:**
```python
class LineItemModel(Base):
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    adjudicated_amount: Mapped[Optional[float]] = mapped_column(Float)
```

**Problem:** Float has precision issues for monetary values.

```python
>>> 0.1 + 0.2
0.30000000000000004  # WRONG
```

**My Correction:**
```python
from sqlalchemy import Numeric
from decimal import Decimal

class LineItemModel(Base):
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    adjudicated_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2))
```

**Impact:** Without this, financial calculations would accumulate rounding errors.

---

### 6. Claim Submission Flow

**AI's Suggestion:**
```python
# Route 1: Submit claim
POST /claims
→ Returns claim with status "pending"

# Route 2: Adjudicate later
POST /claims/{id}/adjudicate
→ Returns adjudication results
```

**Problem:** This doesn't match real-world behavior. Claims are adjudicated upon receipt, not held for manual processing.

**My Correction:**
```python
@router.post("/claims", response_model=ClaimResponse)
async def submit_claim(request: ClaimSubmitRequest):
    """Submit a new claim for adjudication.
    
    The claim will be AUTOMATICALLY adjudicated against the member's policy rules.
    """
    # ... create claim ...
    
    # AUTO-ADJUDICATE immediately
    usage_history = uow.usage.get_by_member(request.member_id)
    engine = AdjudicationEngine()
    results = engine.adjudicate_claim(claim, policy, usage_history)
    
    # Apply results and save
    claim.adjudicate_all(adjudication_map)
    saved_claim = uow.claims.add(claim)
    
    return saved_claim  # Returns fully adjudicated claim
```

**Impact:** Better UX and matches industry standard behavior.

---

### 7. Error Handling: Raw Exceptions

**AI's Generated Code:**
```python
@router.get("/members/{member_id}")
async def get_member(member_id: str):
    member = uow.members.get(member_id)
    return member  # Returns None if not found → 500 error
```

**Problem:** Returns HTTP 500 when member not found instead of 404.

**My Correction:**
```python
@router.get("/members/{member_id}")
async def get_member(member_id: str):
    with DatabaseUnitOfWork() as uow:
        member = uow.members.get(member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member {member_id} not found"
            )
        return member
```

**Impact:** Proper HTTP status codes for API consumers.

---

### 8. Usage Recording Timing

**AI's Generated Code:**
```python
# In submit_claim endpoint
uow.usage.add_record(member_id, usage_record)  # Record usage now
```

**Problem:** Usage should be recorded when claim is PAID, not when adjudicated. A claim could be adjudicated but never paid (if disputed, appealed, etc.).

**My Note:** Documented as a known limitation for future fix.

**Correct Approach (Not Implemented):**
```python
@router.post("/claims/{id}/pay")
async def pay_claim(claim_id: str):
    """Mark claim as paid and record usage."""
    with DatabaseUnitOfWork() as uow:
        claim = uow.claims.get(claim_id)
        claim.status = ClaimStatus.PAID
        claim.paid_at = datetime.utcnow()
        
        # NOW record usage
        for line_item in claim.line_items:
            if line_item.adjudicated_amount > 0:
                uow.usage.add_record(claim.member_id, ...)
        
        uow.commit()
```

**Impact:** Currently, usage is recorded too early, which could affect limit calculations for subsequent claims.

---

### 9. Typo: `paidable` → `payable`

**AI's Generated Code:**
```python
return AdjudicationResult(
    line_item_id=line_item.line_item_id,
    payable=paidable,  # TYPO
    denied=denied,
    reason=reason,
)
```

**Error:**
```
NameError: name 'paidable' is not defined
```

**My Correction:**
```python
payable=payable,  # Fixed
```

**Impact:** Application wouldn't start without this fix.

---

### 10. Missing Import: UsageRecord

**AI's Generated Code:**
```python
from app.repositories.in_memory import UnitOfWork
from app.services.coverage import UsageRecord  # MISSING
```

**Error:**
```
NameError: name 'UsageRecord' is not defined
```

**My Correction:** Added the missing import.

---

## Minor Corrections

### 11. Type Hint Compatibility

**Issue:** Python 3.11 type hints with `list[Claim]` caused runtime errors.

**Fix:** Added `from __future__ import annotations` at top of file.

### 12. DateTime Deprecation

**AI's Code:**
```python
from datetime import datetime
datetime.utcnow()  # Deprecated
```

**Fix:**
```python
from datetime import datetime, timezone
datetime.now(timezone.utc)  # Correct
```

### 13. Claim Number Format

**AI's Suggestion:** `f"claim-{uuid4()}"`

**My Correction:** `f"CLM-{datetime.utcnow().strftime('%Y%m%d')}-{uuid4().hex[:8].upper()}"`

**Reason:** Human-readable claim numbers with date prefix.

### 14. Test Coverage Gaps

**AI Generated:** Basic happy-path tests

**My Additions:**
- Calendar year boundary test
- Multiple line items test (partial approval)
- Large denial review flag test
- Limit exhaustion with partial remaining test

### 15. Documentation: Missing Trade-offs

**AI's Draft:** Listed what was built

**My Addition:** Added "What Was NOT Built" section with reasons:
- No database persistence (started with in-memory)
- No authentication (out of scope)
- No frontend (API-only)
- Incomplete deductible tracking (time budget)

---

## Pattern Analysis

### Types of AI Errors

| Error Type | Count | Severity |
|------------|-------|----------|
| Missing business logic | 4 | Critical |
| Wrong calculation order | 1 | Critical |
| Missing relationships | 1 | Critical |
| Type/precision issues | 2 | High |
| Flow/architecture issues | 2 | Medium |
| Typos/syntax | 1 | Low |
| Missing imports | 1 | Low |
| Deprecation | 1 | Low |

### Root Causes

1. **Domain ignorance** - AI doesn't understand insurance business rules
2. **Context limitations** - AI can't see the full system at once
3. **No execution** - AI can't test its own code
4. **Optimism bias** - AI assumes happy path, misses edge cases

### Prevention Strategies

1. **Specify edge cases explicitly** - "Handle X, Y, Z scenarios"
2. **Ask for explanations** - "Why did you implement it this way?"
3. **Test immediately** - Run AI's code before building on it
4. **Cross-reference** - "Show me 3 alternative approaches"
5. **Verify calculations** - Manually trace financial formulas

---

## Summary

**Total corrections:** 15+  
**Critical fixes:** 6  
**Would have broken system:** 4  
**Would have caused wrong calculations:** 2  
**Would have caused runtime errors:** 3  

**Key lesson:** AI is a powerful tool for accelerating development, but every line of code needs human review. The AI doesn't understand the domain, can't test its code, and makes optimistic assumptions that don't hold in real-world scenarios.

**Recommendation:** Treat AI like a very fast, very confident junior developer. Great for boilerplate and exploration, but all code requires senior review before merging.
