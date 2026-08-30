import sys
import os
backend_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_path)

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import date
from fastapi import HTTPException
import models.user
import models.products
import models.invoice
import models.ai
import models.auth

from models.user import Business as BusinessModel
from models.invoice import InvoiceStatus
from services.analytics import (
    _get_authorized_business,
    total_revenue,
    top_selling_products,
    low_stock_products,
    profit_margins,
)

def mock_db_result(value=None):
    mock_res = MagicMock()
    if isinstance(value, list):
        mock_res.all.return_value = value
    else:
        mock_res.scalar_one_or_none.return_value = value
        mock_res.scalar.return_value = value
        mock_res.one.return_value = value
    return mock_res

@pytest.mark.asyncio
async def test_get_authorized_business_success():
    db = AsyncMock()
    biz_mock = BusinessModel(id=1, user_id=10, name="My Shop")
    db.execute.return_value = mock_db_result(biz_mock)
    
    business = await _get_authorized_business(db, current_user_id=10, business_id=1)
    assert business.id == 1
    assert business.user_id == 10

@pytest.mark.asyncio
async def test_get_authorized_business_not_found():
    db = AsyncMock()
    db.execute.return_value = mock_db_result(None)
    
    with pytest.raises(HTTPException) as excinfo:
        await _get_authorized_business(db, current_user_id=10, business_id=999)
    assert excinfo.value.status_code == 404

@pytest.mark.asyncio
async def test_get_authorized_business_forbidden():
    db = AsyncMock()
    biz_mock = BusinessModel(id=1, user_id=20, name="Other Shop")
    db.execute.return_value = mock_db_result(biz_mock)
    
    with pytest.raises(HTTPException) as excinfo:
        await _get_authorized_business(db, current_user_id=10, business_id=1)
    assert excinfo.value.status_code == 403

@pytest.mark.asyncio
async def test_total_revenue_calculation():
    db = AsyncMock()
    biz_mock = BusinessModel(id=1, user_id=10)
    
    db.execute.side_effect = [
        mock_db_result(biz_mock),
        mock_db_result(1500.0),
        mock_db_result(1000.0)
    ]
    
    res = await total_revenue(db, current_user_id=10, business_id=1)
    assert res["currentMonthRevenue"] == 1500.0
    assert res["lastMonthRevenue"] == 1000.0
    assert res["percentageChange"] == 50.0

@pytest.mark.asyncio
async def test_profit_margins_success():
    db = AsyncMock()
    biz_mock = BusinessModel(id=1, user_id=10)
    
    row_mock = MagicMock()
    row_mock.total_revenue = 200.0
    row_mock.total_cost = 120.0
    row_mock.total_profit = 80.0
    
    db.execute.side_effect = [
        mock_db_result(biz_mock),
        mock_db_result(row_mock)
    ]
    
    margins = await profit_margins(db, current_user_id=10, business_id=1)
    assert margins["totalRevenue"] == 200.0
    assert margins["totalCost"] == 120.0
    assert margins["totalProfit"] == 80.0
    assert margins["marginPercent"] == 40.0

@pytest.mark.asyncio
async def test_top_selling_products():
    db = AsyncMock()
    biz_mock = BusinessModel(id=1, user_id=10)
    
    r1 = MagicMock()
    r1.id = 100
    r1.name = "Apple"
    r1.selling_price = 1.5
    r1.total_qty = 20
    r1.total_revenue = 30.0
    
    db.execute.side_effect = [
        mock_db_result(biz_mock),
        mock_db_result([r1])
    ]
    
    top = await top_selling_products(db, current_user_id=10, business_id=1)
    assert len(top) == 1
    assert top[0]["name"] == "Apple"
    assert top[0]["totalQty"] == 20

@pytest.mark.asyncio
async def test_low_stock_products():
    db = AsyncMock()
    biz_mock = BusinessModel(id=1, user_id=10)
    
    r1 = MagicMock()
    r1.id = 101
    r1.name = "Bread"
    r1.stock = 5
    r1.category = "Bakery"
    
    db.execute.side_effect = [
        mock_db_result(biz_mock),
        mock_db_result([r1])
    ]
    
    low = await low_stock_products(db, current_user_id=10, business_id=1, threshold=10)
    assert len(low) == 1
    assert low[0]["name"] == "Bread"
    assert low[0]["stock"] == 5


@pytest.mark.asyncio
async def test_numeric_analytics_success():
    from services.analytics import numeric_analytics
    db = AsyncMock()
    biz_mock = BusinessModel(id=1, user_id=10)

    db.execute.side_effect = [
        mock_db_result(biz_mock),
        mock_db_result(50000.0),  
        mock_db_result(10),       
        mock_db_result(5),        
    ]

    res = await numeric_analytics(db, current_user_id=10, business_id=1, time="month")
    assert res["totalSales"] == 50000.0
    assert res["totalInvoices"] == 10
    assert res["recentCustomers"] == 5


def test_cache_helpers_with_mock_redis():
    from services.analytics import _get_cache, _set_cache, invalidate_dashboard_cache
    from unittest.mock import patch

    with patch("services.analytics.redisClient") as mock_redis, patch("services.analytics._is_testing", return_value=False):
        mock_redis.get.return_value = '{"totalSales": 123.45}'
        val = _get_cache("dashboard:1:numeric:month")
        assert val == {"totalSales": 123.45}
        mock_redis.get.assert_called_once_with("dashboard:1:numeric:month")

        _set_cache("dashboard:1:numeric:month", {"totalSales": 123.45})
        mock_redis.set.assert_called_once()

        mock_redis.scan_iter.return_value = ["dashboard:1:numeric:month", "dashboard:1:revenue"]
        invalidate_dashboard_cache(1)
        mock_redis.delete.assert_called_once_with("dashboard:1:numeric:month", "dashboard:1:revenue")

