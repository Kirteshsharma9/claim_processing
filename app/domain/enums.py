from enum import Enum


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
    """Standard service types for claims."""
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
