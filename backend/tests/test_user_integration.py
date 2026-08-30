import sys
import os
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime

import models.user
import models.products
import models.invoice
import models.ai
import models.auth

from app import app
from db.database import get_async_db
from middlewares.auth import auth, current_user
from models.user import User as UserModel, Business as BusinessModel

db_mock = None

async def override_get_async_db():
    yield db_mock

def mock_auth():
    return 10

def mock_current_user():
    return 10

client = TestClient(app)

def mock_db_result(value=None):
    mock_res = MagicMock()
    if isinstance(value, list):
        mock_res.scalars.return_value.all.return_value = value
    else:
        mock_res.scalar_one_or_none.return_value = value
        mock_res.scalar_one.return_value = value
    return mock_res

@pytest.fixture(autouse=True)
def reset_db_mock():
    global db_mock
    db_mock = AsyncMock()
    db_mock.add = MagicMock()
    db_mock.commit = AsyncMock()
    db_mock.refresh = AsyncMock()
    db_mock.delete = AsyncMock()
    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[auth] = mock_auth
    app.dependency_overrides[current_user] = mock_current_user
    yield
    app.dependency_overrides.clear()

def test_integration_get_user_profile():
    user = UserModel(
        id=10,
        email="user@example.com",
        name="Integration User",
        businesses=[],
        created_at=datetime.utcnow()
    )
    db_mock.execute.return_value = mock_db_result(user)
    
    response = client.get("/user/10")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["id"] == 10
    assert res_data["name"] == "Integration User"

def test_integration_update_user_profile():
    user_mock = UserModel(
        id=10,
        email="old@example.com",
        name="Old User",
        businesses=[],
        created_at=datetime.utcnow()
    )
    db_mock.execute.side_effect = [
        mock_db_result(user_mock),
        mock_db_result(None),
        mock_db_result(user_mock)
    ]
    
    response = client.patch(
        "/user/10",
        json={
            "name": "Updated User",
            "email": "updated@example.com"
        }
    )
    
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["name"] == "Updated User"
    assert res_data["email"] == "updated@example.com"
    assert db_mock.commit.call_count >= 1

def test_integration_create_business_success():
    biz_mock = BusinessModel(id=50, user_id=10, name="My Shop")
    db_mock.execute.return_value = mock_db_result(None)
    
    def mock_refresh(instance):
        instance.id = 50
    db_mock.refresh.side_effect = mock_refresh
    
    response = client.post(
        "/user/business",
        json={
            "name": "My Shop",
            "gst_number": "27GSTNUMBER1234Z",
            "phone": "9999999999",
            "email": "shop@example.com"
        }
    )
    
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["name"] == "My Shop"
    assert res_data["id"] == 50
    assert db_mock.commit.call_count >= 1

def test_integration_delete_business():
    biz_mock = BusinessModel(id=50, user_id=10, name="My Shop")
    db_mock.execute.return_value = mock_db_result(biz_mock)
    
    response = client.delete("/user/business/50")
    assert response.status_code == 200
    assert db_mock.delete.await_count >= 1
    assert db_mock.commit.call_count >= 1
