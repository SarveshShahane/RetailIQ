import sys
import os
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

import models.user
import models.products
import models.invoice
import models.ai
import models.auth

from app import app
from db.database import get_async_db
from models.user import User as UserModel
from services.auth import hash_password

db_mock = None

async def override_get_async_db():
    yield db_mock

client = TestClient(app)

def mock_db_result(value=None):
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = value
    return mock_res

@pytest.fixture(autouse=True)
def reset_db_mock():
    global db_mock
    db_mock = AsyncMock()
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()
    app.dependency_overrides[get_async_db] = override_get_async_db
    yield
    app.dependency_overrides.clear()

def test_integration_register_success():
    db_mock.execute.return_value = mock_db_result(None)
    
    def mock_refresh(instance):
        instance.id = 100
        instance.created_at = datetime.now()
    db_mock.refresh.side_effect = mock_refresh
    
    response = client.post(
        "/auth/register",
        json={
            "name": "Integration User",
            "email": "integration@example.com",
            "password": "SecurePassword123"
        }
    )
    
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["name"] == "Integration User"
    assert res_data["email"] == "integration@example.com"
    assert res_data["id"] == 100
    assert db_mock.add.call_count >= 1
    assert db_mock.commit.call_count >= 1

def test_integration_register_email_taken():
    existing_user = UserModel(id=1, email="taken@example.com", name="Existing")
    db_mock.execute.return_value = mock_db_result(existing_user)
    
    response = client.post(
        "/auth/register",
        json={
            "name": "New User",
            "email": "taken@example.com",
            "password": "Password123"
        }
    )
    
    assert response.status_code == 400
    res_data = response.json()
    assert "already registered" in res_data["detail"].lower()

def test_integration_login_success():
    hashed = hash_password("SecurePassword123")
    user = UserModel(id=10, email="user@example.com", name="User", password=hashed)
    db_mock.execute.return_value = mock_db_result(user)
    
    response = client.post(
        "/auth/login",
        json={
            "email": "user@example.com",
            "password": "SecurePassword123"
        }
    )
    
    assert response.status_code == 200
    res_data = response.json()
    assert "access_token" in res_data
    assert res_data["user"]["id"] == 10
    assert "refresh_token" in response.cookies
    assert db_mock.add.call_count >= 1
    assert db_mock.commit.call_count >= 1

def test_integration_login_invalid_credentials():
    db_mock.execute.return_value = mock_db_result(None)
    
    response = client.post(
        "/auth/login",
        json={
            "email": "missing@example.com",
            "password": "Password123"
        }
    )
    
    assert response.status_code == 401
    res_data = response.json()
    assert "credentials" in res_data["detail"].lower()
