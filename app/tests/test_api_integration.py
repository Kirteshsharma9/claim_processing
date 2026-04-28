"""
Test-Driven Development for API Integration Tests.

Integration tests for the FastAPI application endpoints.

These tests verify:
- End-to-end API workflows
- Request/response validation
- Error handling
- Database integration
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine
from app.repositories.sqlalchemy import DatabaseUnitOfWork
from app.domain.models import Member, Policy, CoverageRule, Money
from app.domain.value_objects import PolicyPeriod
from app.domain.enums import ServiceType, CoverageLimitType


@pytest.fixture(scope="function")
def test_db():
    """Create test database tables."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with test database."""
    return TestClient(app)


@pytest.fixture
def sample_member_data():
    """Sample member request data."""
    return {
        "first_name": "John",
        "last_name": "Doe",
        "date_of_birth": "1985-06-15",
        "email": "john.doe@example.com",
        "phone": "555-123-4567",
    }


@pytest.fixture
def sample_policy_data():
    """Sample policy request data."""
    return {
        "member_id": None,  # Will be set dynamically
        "policy_number": "POL-2026-001",
        "group_number": "GRP-001",
        "policy_start": "2026-01-01",
        "policy_end": "2026-12-31",
        "coverage_rules": [
            {
                "service_type": "laboratory",
                "coverage_percentage": 1.0,
                "limit_type": "annual_max",
                "limit_amount": 1000.0,
                "deductible_applies": False,
            },
            {
                "service_type": "specialist",
                "coverage_percentage": 0.8,
                "limit_type": "annual_max",
                "limit_amount": 5000.0,
                "deductible_applies": False,
            },
        ],
    }


@pytest.fixture
def sample_claim_data():
    """Sample claim request data."""
    return {
        "member_id": None,  # Will be set dynamically
        "diagnosis_codes": ["Z00.00"],
        "line_items": [
            {
                "service_type": "laboratory",
                "service_date": "2026-06-15",
                "description": "Blood work panel",
                "amount": 300.0,
                "provider": {
                    "name": "LabCorp",
                    "npi": "1234567890",
                },
            },
        ],
    }


class TestMemberEndpoints:
    """Tests for Member API endpoints."""

    def test_create_member(self, client, sample_member_data):
        """Should create a new member."""
        response = client.post("/api/v1/members", json=sample_member_data)

        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "John"
        assert data["last_name"] == "Doe"
        assert data["date_of_birth"] == "1985-06-15"
        assert "member_id" in data

    def test_get_member(self, client, sample_member_data):
        """Should get member by ID."""
        # Create member first
        create_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = create_response.json()["member_id"]

        # Get member
        response = client.get(f"/api/v1/members/{member_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["member_id"] == member_id
        assert data["email"] == "john.doe@example.com"

    def test_get_member_not_found(self, client):
        """Should return 404 for non-existent member."""
        response = client.get("/api/v1/members/nonexistent-id")

        assert response.status_code == 404

    def test_list_members(self, client, sample_member_data):
        """Should list all members."""
        # Create multiple members
        client.post("/api/v1/members", json=sample_member_data)
        sample_member_data["email"] = "jane@example.com"
        client.post("/api/v1/members", json=sample_member_data)

        response = client.get("/api/v1/members")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_create_member_validation(self, client):
        """Should validate required fields."""
        invalid_data = {
            "first_name": "",  # Empty first name
            "last_name": "Doe",
            "date_of_birth": "1985-06-15",
        }

        response = client.post("/api/v1/members", json=invalid_data)

        assert response.status_code == 422  # Validation error


class TestPolicyEndpoints:
    """Tests for Policy API endpoints."""

    def test_create_policy(self, client, sample_member_data, sample_policy_data):
        """Should create a new policy for a member."""
        # Create member first
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        # Create policy
        sample_policy_data["member_id"] = member_id
        response = client.post("/api/v1/policies", json=sample_policy_data)

        assert response.status_code == 200
        data = response.json()
        assert data["policy_number"] == "POL-2026-001"
        assert len(data["coverage_rules"]) == 2

    def test_get_policy(self, client, sample_member_data, sample_policy_data):
        """Should get policy by ID."""
        # Create member and policy
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        policy_response = client.post("/api/v1/policies", json=sample_policy_data)
        policy_id = policy_response.json()["policy_id"]

        # Get policy
        response = client.get(f"/api/v1/policies/{policy_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["policy_id"] == policy_id

    def test_get_policy_not_found(self, client):
        """Should return 404 for non-existent policy."""
        response = client.get("/api/v1/policies/nonexistent-id")

        assert response.status_code == 404

    def test_get_member_policy(self, client, sample_member_data, sample_policy_data):
        """Should get policy for a specific member."""
        # Create member and policy
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        client.post("/api/v1/policies", json=sample_policy_data)

        # Get member's policy
        response = client.get(f"/api/v1/members/{member_id}/policy")

        assert response.status_code == 200
        data = response.json()
        assert data["member_id"] == member_id

    def test_create_policy_member_not_found(self, client, sample_policy_data):
        """Should return 404 when creating policy for non-existent member."""
        sample_policy_data["member_id"] = "nonexistent-member"

        response = client.post("/api/v1/policies", json=sample_policy_data)

        assert response.status_code == 404

    def test_get_member_policy_not_found(self, client, sample_member_data):
        """Should return 404 when member has no policy."""
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        response = client.get(f"/api/v1/members/{member_id}/policy")

        assert response.status_code == 404


class TestClaimEndpoints:
    """Tests for Claim API endpoints."""

    def test_submit_claim(
        self, client, sample_member_data, sample_policy_data, sample_claim_data
    ):
        """Should submit a new claim for adjudication."""
        # Setup: Create member and policy
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        client.post("/api/v1/policies", json=sample_policy_data)

        # Submit claim
        sample_claim_data["member_id"] = member_id
        response = client.post("/api/v1/claims", json=sample_claim_data)

        assert response.status_code == 200
        data = response.json()
        assert "claim_id" in data
        assert "claim_number" in data
        assert data["member_id"] == member_id
        assert len(data["line_items"]) == 1

    def test_get_claim(self, client, sample_member_data, sample_policy_data, sample_claim_data):
        """Should get claim by ID."""
        # Setup
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        client.post("/api/v1/policies", json=sample_policy_data)

        sample_claim_data["member_id"] = member_id
        claim_response = client.post("/api/v1/claims", json=sample_claim_data)
        claim_id = claim_response.json()["claim_id"]

        # Get claim
        response = client.get(f"/api/v1/claims/{claim_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["claim_id"] == claim_id

    def test_list_claims(self, client, sample_member_data, sample_policy_data, sample_claim_data):
        """Should list all claims."""
        # Setup
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        client.post("/api/v1/policies", json=sample_policy_data)

        # Submit multiple claims
        sample_claim_data["member_id"] = member_id
        client.post("/api/v1/claims", json=sample_claim_data)
        sample_claim_data["diagnosis_codes"] = ["Z00.01"]
        client.post("/api/v1/claims", json=sample_claim_data)

        response = client.get("/api/v1/claims")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2

    def test_get_claim_adjudication(
        self, client, sample_member_data, sample_policy_data, sample_claim_data
    ):
        """Should get detailed adjudication results for a claim."""
        # Setup
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        client.post("/api/v1/policies", json=sample_policy_data)

        sample_claim_data["member_id"] = member_id
        claim_response = client.post("/api/v1/claims", json=sample_claim_data)
        claim_id = claim_response.json()["claim_id"]

        # Get adjudication
        response = client.get(f"/api/v1/claims/{claim_id}/adjudication")

        assert response.status_code == 200
        data = response.json()
        assert data["claim_id"] == claim_id
        assert "results" in data
        assert len(data["results"]) > 0

    def test_get_claim_explanation(
        self, client, sample_member_data, sample_policy_data, sample_claim_data
    ):
        """Should get human-readable explanation for claim decision."""
        # Setup
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        client.post("/api/v1/policies", json=sample_policy_data)

        sample_claim_data["member_id"] = member_id
        claim_response = client.post("/api/v1/claims", json=sample_claim_data)
        claim_id = claim_response.json()["claim_id"]

        # Get explanation
        response = client.get(f"/api/v1/claims/{claim_id}/explanation")

        assert response.status_code == 200
        data = response.json()
        assert data["claim_id"] == claim_id
        assert "summary" in data
        assert "line_item_explanations" in data

    def test_list_member_claims(
        self, client, sample_member_data, sample_policy_data, sample_claim_data
    ):
        """Should list all claims for a member."""
        # Setup
        member_response = client.post("/api/v1/members", json=sample_member_data)
        print(member_response)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        client.post("/api/v1/policies", json=sample_policy_data)

        sample_claim_data["member_id"] = member_id
        client.post("/api/v1/claims", json=sample_claim_data)

        response = client.get(f"/api/v1/members/{member_id}/claims")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert all(claim["member_id"] == member_id for claim in data)

    def test_submit_claim_member_not_found(self, client, sample_claim_data):
        """Should return 404 when submitting claim for non-existent member."""
        sample_claim_data["member_id"] = "nonexistent-member"

        response = client.post("/api/v1/claims", json=sample_claim_data)

        assert response.status_code == 404

    def test_submit_claim_no_policy(self, client, sample_member_data, sample_claim_data):
        """Should return 404 when member has no policy."""
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_claim_data["member_id"] = member_id

        response = client.post("/api/v1/claims", json=sample_claim_data)

        assert response.status_code == 404

    def test_claim_adjudication_results(
        self, client, sample_member_data, sample_policy_data, sample_claim_data
    ):
        """Should correctly adjudicate claim with mixed results."""
        # Setup with specific coverage rules
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        # Policy with 100% lab coverage, no cosmetic coverage
        policy_data = {
            "member_id": member_id,
            "policy_number": "POL-2026-001",
            "policy_start": "2026-01-01",
            "policy_end": "2026-12-31",
            "coverage_rules": [
                {
                    "service_type": "laboratory",
                    "coverage_percentage": 1.0,
                    "limit_type": "annual_max",
                    "limit_amount": 1000.0,
                }
            ],
        }
        client.post("/api/v1/policies", json=policy_data)

        # Claim with lab (covered) and cosmetic (not covered)
        claim_data = {
            "member_id": member_id,
            "line_items": [
                {
                    "service_type": "laboratory",
                    "service_date": "2026-06-15",
                    "description": "Lab test",
                    "amount": 300.0,
                },
                {
                    "service_type": "cosmetic",
                    "service_date": "2026-06-15",
                    "description": "Cosmetic procedure",
                    "amount": 500.0,
                },
            ],
        }

        claim_response = client.post("/api/v1/claims", json=claim_data)
        claim_id = claim_response.json()["claim_id"]

        # Get adjudication
        adj_response = client.get(f"/api/v1/claims/{claim_id}/adjudication")
        data = adj_response.json()

        # Should have mixed results
        print(data)
        assert data["total_approved"] == '300.00'
        assert data["total_denied"] == '500.00'


class TestDisputeEndpoints:
    """Tests for Dispute API endpoints."""

    def test_create_dispute(
        self, client, sample_member_data, sample_policy_data, sample_claim_data
    ):
        """Should create a dispute for a claim."""
        # Setup
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        client.post("/api/v1/policies", json=sample_policy_data)

        sample_claim_data["member_id"] = member_id
        claim_response = client.post("/api/v1/claims", json=sample_claim_data)
        claim_id = claim_response.json()["claim_id"]

        # Create dispute
        dispute_data = {
            "line_item_ids": [
                claim_response.json()["line_items"][0]["line_item_id"]
            ],
            "reason": "This service was medically necessary and should be covered.",
        }

        response = client.post(f"/api/v1/claims/{claim_id}/disputes", json=dispute_data)

        assert response.status_code == 200
        data = response.json()
        assert data["claim_id"] == claim_id
        assert data["status"] == "open"

    def test_list_claim_disputes(
        self, client, sample_member_data, sample_policy_data, sample_claim_data
    ):
        """Should list all disputes for a claim."""
        # Setup
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        client.post("/api/v1/policies", json=sample_policy_data)

        sample_claim_data["member_id"] = member_id
        claim_response = client.post("/api/v1/claims", json=sample_claim_data)
        claim_id = claim_response.json()["claim_id"]

        # Create dispute
        dispute_data = {
            "line_item_ids": [
                claim_response.json()["line_items"][0]["line_item_id"]
            ],
            "reason": "Disputed",
        }
        client.post(f"/api/v1/claims/{claim_id}/disputes", json=dispute_data)

        # List disputes
        response = client.get(f"/api/v1/claims/{claim_id}/disputes")

        assert response.status_code == 200

    def test_get_dispute(
        self, client, sample_member_data, sample_policy_data, sample_claim_data
    ):
        """Should get dispute by ID."""
        # Setup
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        client.post("/api/v1/policies", json=sample_policy_data)

        sample_claim_data["member_id"] = member_id
        claim_response = client.post("/api/v1/claims", json=sample_claim_data)
        claim_id = claim_response.json()["claim_id"]

        # Create dispute
        dispute_data = {
            "line_item_ids": [
                claim_response.json()["line_items"][0]["line_item_id"]
            ],
            "reason": "Disputed: something went wrong.",
        }
        dispute_response = client.post(
            f"/api/v1/claims/{claim_id}/disputes", json=dispute_data
        )
        print(dispute_response.json())

        dispute_id = dispute_response.json()["dispute_id"]

        # Get dispute
        response = client.get(f"/api/v1/disputes/{dispute_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["dispute_id"] == dispute_id

    def test_create_dispute_claim_not_found(self, client):
        """Should return 404 for non-existent claim."""
        dispute_data = {
            "line_item_ids": ["item-1"],
            "reason": "Disputed: something went wrong",
        }

        response = client.post("/api/v1/claims/nonexistent/disputes", json=dispute_data)

        assert response.status_code == 404

    def test_create_dispute_invalid_line_item(
        self, client, sample_member_data, sample_policy_data, sample_claim_data
    ):
        """Should return 400 when line item not in claim."""
        # Setup
        member_response = client.post("/api/v1/members", json=sample_member_data)
        member_id = member_response.json()["member_id"]

        sample_policy_data["member_id"] = member_id
        client.post("/api/v1/policies", json=sample_policy_data)

        sample_claim_data["member_id"] = member_id
        claim_response = client.post("/api/v1/claims", json=sample_claim_data)
        claim_id = claim_response.json()["claim_id"]

        # Try to dispute non-existent line item
        dispute_data = {
            "line_item_ids": ["nonexistent-item"],
            "reason": "Disputed: something went wrong",
        }

        response = client.post(
            f"/api/v1/claims/{claim_id}/disputes", json=dispute_data
        )

        assert response.status_code == 400


class TestFullWorkflow:
    """End-to-end workflow tests."""

    def test_complete_claim_workflow(
        self, client, sample_member_data, sample_policy_data, sample_claim_data
    ):
        """Test complete workflow from member creation to claim explanation."""
        # 1. Create member
        member_response = client.post("/api/v1/members", json=sample_member_data)
        assert member_response.status_code == 200
        member_id = member_response.json()["member_id"]

        # 2. Create policy with coverage
        sample_policy_data["member_id"] = member_id
        policy_response = client.post("/api/v1/policies", json=sample_policy_data)
        assert policy_response.status_code == 200
        policy_id = policy_response.json()["policy_id"]

        # 3. Submit claim
        sample_claim_data["member_id"] = member_id
        claim_response = client.post("/api/v1/claims", json=sample_claim_data)
        assert claim_response.status_code == 200
        claim_id = claim_response.json()["claim_id"]
        claim_data = claim_response.json()

        # Verify claim was adjudicated
        assert claim_data["status"] in [
            "approved",
            "partially_approved",
            "denied",
        ]

        # 4. Get adjudication details
        adj_response = client.get(f"/api/v1/claims/{claim_id}/adjudication")
        assert adj_response.status_code == 200

        # 5. Get explanation
        exp_response = client.get(f"/api/v1/claims/{claim_id}/explanation")
        assert exp_response.status_code == 200
        assert "summary" in exp_response.json()

        # 6. List member's claims
        claims_response = client.get(f"/api/v1/members/{member_id}/claims")
        assert claims_response.status_code == 200
        assert len(claims_response.json()) >= 1

        # 7. Get member's policy
        policy_get_response = client.get(f"/api/v1/members/{member_id}/policy")
        assert policy_get_response.status_code == 200
