"""
Claims Processing System

A FastAPI-based API for processing insurance claims with coverage rule adjudication.

Usage:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

API Documentation:
    Swagger UI: http://localhost:8000/docs
    ReDoc: http://localhost:8000/redoc
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for database initialization."""
    # Startup: Initialize database tables
    init_db()
    yield
    # Shutdown: cleanup if needed

app = FastAPI(
    title="Claims Processing System",
    lifespan=lifespan,
    description="""
## Insurance Claims Processing API

This API provides endpoints for:

### Members
- Create and manage insurance members
- View member details

### Policies
- Create policies with coverage rules
- Define coverage limits and percentages by service type

### Claims
- Submit claims with line items
- Automatic adjudication against coverage rules
- View claim status and explanations

### Disputes
- File disputes for denied claims
- Track dispute status

## Key Features

- **Automatic Adjudication**: Claims are automatically evaluated against policy coverage rules
- **Partial Approvals**: Line items can be individually approved/denied
- **Explanation Generation**: Human-readable explanations for all decisions
- **Coverage Tracking**: Tracks usage against annual and lifetime limits
    """,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")


@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {
        "service": "Claims Processing System",
        "version": "0.1.0",
        "status": "healthy"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "components": {
            "api": "ok",
            "storage": "ok",  # In-memory, always ok
        }
    }
