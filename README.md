# Claims Processing System

Insurance claims processing system with automated coverage rule adjudication.

## Quick Start

```bash
# Install dependencies
uv venv
source .venv/bin/activate
# Installation Commands 
pip install -r requirements.txt
# or
uv sync

# Run the server (database auto-initializes)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Open API docs
open http://localhost:8000/docs
```

## Database

The system uses SQLite with SQLAlchemy ORM. The database file (`claims.db`) is created automatically on first run.

```bash
# Database location
./claims.db

# To use a different database, edit DATABASE_URL in app/database.py
```

See [docs/database-schema.md](docs/database-schema.md) for the full schema and ER diagram.

## Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest app/tests

# Run linter
ruff check app/
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/members` | Create member |
| GET | `/api/v1/members/{id}` | Get member |
| POST | `/api/v1/policies` | Create policy with coverage rules |
| GET | `/api/v1/members/{id}/policy` | Get member's policy |
| POST | `/api/v1/claims` | Submit claim (auto-adjudicated) |
| GET | `/api/v1/claims/{id}` | Get claim |
| GET | `/api/v1/claims/{id}/adjudication` | Get adjudication results |
| GET | `/api/v1/claims/{id}/explanation` | Get human-readable explanation |
| POST | `/api/v1/claims/{id}/disputes` | File dispute |

## Example Usage

### 1. Create a Member

```bash
curl -X POST http://localhost:8000/api/v1/members \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "John",
    "last_name": "Doe",
    "date_of_birth": "1985-06-15",
    "email": "john@example.com"
  }'
```

### 2. Create a Policy with Coverage Rules

```bash
curl -X POST http://localhost:8000/api/v1/policies \
  -H "Content-Type: application/json" \
  -d '{
    "member_id": "<member-id>",
    "policy_number": "POL-2026-001",
    "policy_start": "2026-01-01",
    "policy_end": "2026-12-31",
    "coverage_rules": [
      {
        "service_type": "preventive",
        "coverage_percentage": 1.0,
        "limit_type": "annual_max",
        "limit_amount": 1000,
        "deductible_applies": false
      },
      {
        "service_type": "specialist",
        "coverage_percentage": 0.8,
        "limit_type": "annual_max",
        "limit_amount": 5000,
        "deductible_applies": true,
        "deductible_amount": 250
      }
    ]
  }'
```

### 3. Submit a Claim

```bash
curl -X POST http://localhost:8000/api/v1/claims \
  -H "Content-Type: application/json" \
  -d '{
    "member_id": "<member-id>",
    "diagnosis_codes": ["Z00.00"],
    "line_items": [
      {
        "service_type": "preventive",
        "service_date": "2026-06-15",
        "description": "Annual physical",
        "amount": 200
      },
      {
        "service_type": "laboratory",
        "service_date": "2026-06-15",
        "description": "Blood work",
        "amount": 150
      }
    ]
  }'
```

### 4. Get Claim Explanation

```bash
curl http://localhost:8000/api/v1/claims/<claim-id>/explanation
```

## Project Structure

```
.
├── app/
│   ├── main.py              # FastAPI application
│   ├── api/
│   │   └── routes.py        # API endpoints
│   ├── domain/
│   │   ├── models.py        # Domain entities
│   │   ├── enums.py         # Enums
│   │   └── value_objects.py # Money, DateRange
│   ├── services/
│   │   ├── adjudication.py  # Core rule engine
│   │   ├── coverage.py      # Coverage tracking
│   │   └── explanation.py   # Explanation generation
│   ├── repositories/
│   │   └── in_memory.py     # In-memory storage
│   └── tests/
│       ├── test_adjudication.py
│       └── test_explanation.py
├── docs/
│   ├── domain-model.md      # Entities, relationships, state machines
│   ├── decisions.md         # Trade-offs and assumptions
│   └── self-review.md       # Honest assessment
├── ai-artifacts/            # AI chat exports
└── requirements.txt
```

## Coverage Rules

The system supports these coverage limit types:

| Type | Description |
|------|-------------|
| `per_occurrence` | Reset after each claim |
| `per_visit` | Same as per_occurrence |
| `annual_max` | Resets each calendar year |
| `per_calendar_year` | Same as annual_max |
| `lifetime_max` | Never resets |

## Adjudication Process

1. **Rule Matching** - Find coverage rule for service type and date
2. **Limit Check** - Verify remaining limit
3. **Calculate Payment** - Apply coverage percentage, cap by limit
4. **Deductible** - Apply deductible if applicable
5. **Review Flag** - Flag high-dollar or large-denial claims
6. **Explanation** - Generate human-readable reason

## Running Tests

```bash
# Run all tests
pytest app/tests -v

# Run specific test file
pytest app/tests/test_adjudication.py -v

# Run with coverage
pytest app/tests --cov=app --cov-report=html
```

## Documentation

- [Domain Model](docs/domain-model.md) - Entities, relationships, state machines
- [Decisions](docs/decisions.md) - Trade-offs and assumptions
- [Self-Review](docs/self-review.md) - Honest assessment of the code

## AI Artifacts

Chat sessions and prompts from AI collaboration are in `ai-artifacts/`.
