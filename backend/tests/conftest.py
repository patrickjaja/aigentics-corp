"""Pytest configuration and shared fixtures."""

import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Database URL for testing
TEST_DATABASE_URL = "postgresql+asyncpg://offer_agent:secure_password@localhost:5432/offer_agent_test"

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_engine():
    """Create async database engine for testing."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a new database session for each test."""
    async_session = sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for API testing."""
    async with AsyncClient(
        base_url="http://localhost:8000/v1",
        headers={"X-API-Key": "test_api_key_123"}
    ) as client:
        yield client


@pytest.fixture
def valid_language() -> str:
    """Return a valid language code."""
    return "en"


@pytest.fixture
def valid_conversation_id() -> str:
    """Return a valid UUID for conversation."""
    return str(uuid4())


@pytest.fixture
def valid_offer_id() -> str:
    """Return a valid UUID for offer."""
    return str(uuid4())


@pytest.fixture
def valid_customer_id() -> str:
    """Return a valid UUID for customer."""
    return str(uuid4())


@pytest.fixture
def valid_workflow_id() -> str:
    """Return a valid UUID for workflow."""
    return str(uuid4())


@pytest.fixture
def sample_customer_data() -> dict:
    """Return valid customer data with GDPR consent."""
    return {
        "company_name": "Test GmbH",
        "contact_person": "Max Mustermann",
        "email": "max@test.de",
        "phone": "+491701234567",
        "language_preference": "de",
        "gdpr_consent": {
            "given": True,
            "purposes": ["offer_generation"],
            "consent_text_version": "1.0",
            "ip_address": "192.168.1.1"
        }
    }


@pytest.fixture
def bearer_token() -> str:
    """Return a valid JWT bearer token for admin endpoints."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test_token"
