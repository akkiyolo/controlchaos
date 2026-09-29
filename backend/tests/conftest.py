"""Pytest test configuration and fixtures."""

import os

# Set test environment variables before importing app
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

TEST_DB_FILE = Path(__file__).resolve().parent / "test_temp.db"
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE}"
os.environ["JWT_SECRET"] = "test-secret-key-at-least-32-chars-long-123456"
os.environ["AUDIT_HASH_SALT"] = "test-audit-salt"
os.environ["LLM_PROVIDER"] = "mock"

from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.db import Base, get_db, get_engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.entities import User  # noqa: E402


@pytest.fixture(scope="session")
def test_engine():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    if TEST_DB_FILE.exists():
        try:
            TEST_DB_FILE.unlink()
        except Exception:
            pass


@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provides a fresh transactional session for each test function."""
    connection = test_engine.connect()
    transaction = connection.begin()
    SessionTest = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = SessionTest()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_users(db_session):
    """Creates a full suite of users with distinct roles."""
    roles = ["admin", "control_owner", "reviewer", "analyst", "auditor"]
    users = {}
    for r in roles:
        u = User(
            email=f"{r}@test.local",
            name=f"Test {r.capitalize()}",
            role=r,
            password_hash=get_password_hash("TestPassword123!"),
            is_active=True,
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
        users[r] = u
    return users


@pytest.fixture
def auth_headers(test_users):
    """Provides valid JWT Bearer authorization headers per role."""
    headers = {}
    for role, user in test_users.items():
        token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
        headers[role] = {"Authorization": f"Bearer {token}"}
    return headers
