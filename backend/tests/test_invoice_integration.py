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
from models.invoice import Invoice as InvoiceModel, InvoiceStatus, InvoiceSource

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
    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[current_user] = mock_current_user
    yield
    app.dependency_overrides.clear()

def test_integration_list_invoices():
    biz_mock = BusinessModel(id=1, user_id=10, name="My Shop")
    invoices = [
        InvoiceModel(id=1, business_id=1, status=InvoiceStatus.PAID, source=InvoiceSource.ONLINE, subtotal=Decimal("100"), tax=Decimal("0"), discount=Decimal("0"), total=Decimal("100"), created_at=datetime.utcnow(), updated_at=datetime.utcnow(), items=[])
    ]
    
    db_mock.execute.side_effect = [
        mock_db_result(biz_mock),
        mock_db_result(invoices),
        mock_db_result(1)
    ]
    
    response = client.get("/invoice/list?business_id=1&page=1&limit=10")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["total"] == 1
    assert len(res_data["items"]) == 1
    assert res_data["items"][0]["status"] == "PAID"
