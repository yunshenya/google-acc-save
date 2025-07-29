import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app, Account, Base

# Use in-memory SQLite for testing
DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest_asyncio.fixture
async def client():
    # Create tables in the in-memory database
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    # Drop tables after tests
    Base.metadata.drop_all(bind=engine)

@pytest_asyncio.fixture
async def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.mark.asyncio
async def test_create_account(client):
    # Test successful account creation
    response = client.post(
        "/accounts/",
        json={"account": "test@example.com", "password": "password123", "type": 1, "code": "a" * 32}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["account"] == "test@example.com"
    assert data["password"] == "password123"
    assert data["type"] == 1
    assert data["status"] == 0
    assert data["code"] == "a" * 32

    # Test duplicate account creation
    response = client.post(
        "/accounts/",
        json={"account": "test@example.com", "password": "password456", "type": 2, "code": "b" * 32}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "账号已存在"

@pytest.mark.asyncio
async def test_get_unique_account(client, db_session):
    # Create an account with status=0
    account = Account(
        account="unique@example.com",
        password="password123",
        type=1,
        status=0,
        code="a" * 32
    )
    db_session.add(account)
    db_session.commit()

    # Test retrieving unique account
    response = client.get("/account/unique")
    assert response.status_code == 200
    data = response.json()
    assert data["account"] == "unique@example.com"
    assert data["status"] == 1  # Status should be updated to 1
    assert data["code"] == "a" * 32

    # Test when no account with status=0 exists
    response = client.get("/account/unique")
    assert response.status_code == 404
    assert response.json()["detail"] == "没有可用的账号（status=0）"

@pytest.mark.asyncio
async def test_update_account(client, db_session):
    # Create an account
    account = Account(
        account="update@example.com",
        password="password123",
        type=1,
        status=0,
        code="a" * 32
    )
    db_session.add(account)
    db_session.commit()
    account_id = account.id

    # Test updating account
    response = client.put(
        f"/accounts/{account_id}",
        json={"account": "updated@example.com", "password": "newpassword", "type": 2, "status": 1, "code": "b" * 32}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["account"] == "updated@example.com"
    assert data["password"] == "newpassword"
    assert data["type"] == 2
    assert data["status"] == 1
    assert data["code"] == "b" * 32

    # Test updating non-existent account
    response = client.put(
        "/accounts/999",
        json={"account": "nonexistent@example.com"}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "账号不存在"

@pytest.mark.asyncio
async def test_get_all_accounts(client, db_session):
    # Create multiple accounts
    accounts = [
        Account(account=f"test{i}@example.com", password=f"password{i}", type=i, status=i % 2, code=f"{i}" * 32)
        for i in range(3)
    ]
    db_session.add_all(accounts)
    db_session.commit()

    # Test retrieving all accounts
    response = client.get("/accounts/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["account"] == "test0@example.com"
    assert data[1]["account"] == "test1@example.com"
    assert data[2]["account"] == "test2@example.com"

@pytest.mark.asyncio
async def test_status_endpoint(client):
    response = client.get("/status")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
