import sys
import os
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

import pytest
from decimal import Decimal
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
from middlewares.auth import auth, current_user
from models.user import Business as BusinessModel
from models.products import Product as ProductModel

db_mock = None

async def override_get_async_db():
    yield db_mock

def mock_current_user():
    return 10

app.dependency_overrides[get_async_db] = override_get_async_db
app.dependency_overrides[current_user] = mock_current_user

client = TestClient(app)

def mock_db_result(value=None):
    mock_res = MagicMock()
    if isinstance(value, list):
        mock_res.scalars.return_value.all.return_value = value
        mock_res.scalar.return_value = len(value)
    else:
        mock_res.scalar_one_or_none.return_value = value
        mock_res.scalar_one.return_value = value
        mock_res.scalar.return_value = value
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
    app.dependency_overrides[current_user] = mock_current_user
    yield
    app.dependency_overrides.clear()

def test_integration_list_products():
    biz_mock = BusinessModel(id=1, user_id=10, name="My Shop")
    prods = [
        ProductModel(id=100, name="Milk", business_id=1, original_price=Decimal("50"), selling_price=Decimal("45"), stock=10, created_at=datetime.utcnow(), updated_at=datetime.utcnow()),
        ProductModel(id=101, name="Bread", business_id=1, original_price=Decimal("30"), selling_price=Decimal("25"), stock=5, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    ]
    db_mock.execute.side_effect = [
        mock_db_result(biz_mock),
        mock_db_result(prods),
        mock_db_result(2)
    ]
    
    response = client.get("/products/?business_id=1&page=1&limit=10")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["total"] == 2
    assert len(res_data["items"]) == 2
    assert res_data["items"][0]["name"] == "Milk"

def test_integration_create_product():
    biz_mock = BusinessModel(id=1, user_id=10, name="My Shop")
    db_mock.execute.return_value = mock_db_result(biz_mock)
    
    def mock_refresh(instance):
        instance.id = 100
        instance.created_at = datetime.utcnow()
        instance.updated_at = datetime.utcnow()
    db_mock.refresh.side_effect = mock_refresh
    
    response = client.post(
        "/products/",
        json={
            "name": "Milk",
            "original_price": "50.00",
            "selling_price": "45.00",
            "stock": 10,
            "business_id": 1
        }
    )
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["id"] == 100
    assert res_data["name"] == "Milk"
    assert db_mock.add.call_count >= 1
    assert db_mock.commit.call_count >= 1

def test_integration_delete_product():
    biz_mock = BusinessModel(id=1, user_id=10, name="My Shop")
    prod_mock = ProductModel(id=100, name="Milk", business_id=1, original_price=Decimal("50"), selling_price=Decimal("45"), stock=10)
    
    db_mock.execute.side_effect = [
        mock_db_result(prod_mock),
        mock_db_result(biz_mock)
    ]
    
    response = client.delete("/products/100")
    assert response.status_code == 204
    assert db_mock.delete.await_count >= 1
    assert db_mock.commit.call_count >= 1
