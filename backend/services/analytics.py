import calendar
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import case, cast, Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.invoice import Invoice, InvoiceItem, InvoiceStatus, Customer, Payment
from models.products import Product
from models.user import Business
from redis_client import redisClient

DASHBOARD_CACHE_TTL = 300  


def _is_testing() -> bool:
    return "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ


def _get_cache(key: str) -> Any | None:
    if _is_testing():
        return None
    try:
        data = redisClient.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        print(f"Redis cache read error ({key}): {e}")
    return None


def _set_cache(key: str, data: Any, ex: int = DASHBOARD_CACHE_TTL) -> None:
    if _is_testing():
        return
    try:
        redisClient.set(key, json.dumps(data), ex=ex)
    except Exception as e:
        print(f"Redis cache write error ({key}): {e}")


def invalidate_dashboard_cache(business_id: int) -> None:
    """Invalidate all cached dashboard analytics for a given business."""
    if _is_testing():
        return
    try:
        pattern = f"dashboard:{business_id}:*"
        keys = list(redisClient.scan_iter(match=pattern, count=100))
        if keys:
            redisClient.delete(*keys)
    except Exception as e:
        print(f"Redis cache invalidation error for business {business_id}: {e}")


async def _get_authorized_business(
    db: AsyncSession, current_user_id: int, business_id: int
) -> Business:
    cache_key = f"business:{business_id}"
    cached_biz = _get_cache(cache_key)
    if cached_biz:
        if cached_biz.get("user_id") != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this business",
            )
        return Business(
            id=cached_biz.get("id"),
            user_id=cached_biz.get("user_id"),
            name=cached_biz.get("name"),
        )

    result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found",
        )
    if business.user_id != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this business",
        )

    _set_cache(
        cache_key,
        {"id": business.id, "user_id": business.user_id, "name": business.name},
        ex=3600,
    )
    return business


async def numeric_analytics(
    db: AsyncSession,
    current_user_id: int,
    business_id: int,
    time: str = "month",
) -> dict:
    await _get_authorized_business(db, current_user_id, business_id)

    cache_key = f"dashboard:{business_id}:numeric:{time}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    now = datetime.now(timezone.utc)
    if time == "today":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time == "week":
        start_date = now - timedelta(days=7)
    elif time == "month":
        start_date = now - timedelta(days=30)
    elif time == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = datetime.min.replace(tzinfo=timezone.utc)

    sales_query = select(func.sum(Invoice.total)).where(
        Invoice.business_id == business_id,
        Invoice.status == InvoiceStatus.PAID,
        Invoice.created_at >= start_date,
    )
    sales_result = await db.execute(sales_query)
    total_sales = sales_result.scalar() or 0.0

    count_query = select(func.count(Invoice.id)).where(
        Invoice.business_id == business_id,
        Invoice.created_at >= start_date,
    )
    count_result = await db.execute(count_query)
    total_invoices = count_result.scalar() or 0

    customer_query = select(func.count(func.distinct(Invoice.customer_id))).where(
        Invoice.business_id == business_id,
        Invoice.customer_id.isnot(None),
        Invoice.created_at >= start_date,
    )
    customer_result = await db.execute(customer_query)
    recent_customers = customer_result.scalar() or 0

    res = {
        "totalSales": float(total_sales),
        "totalInvoices": total_invoices,
        "recentCustomers": recent_customers,
    }
    _set_cache(cache_key, res)
    return res


async def total_revenue(
    db: AsyncSession,
    current_user_id: int,
    business_id: int,
) -> dict:
    await _get_authorized_business(db, current_user_id, business_id)

    cache_key = f"dashboard:{business_id}:revenue"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    now = datetime.now(timezone.utc)

    curr_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_day = calendar.monthrange(now.year, now.month)[1]
    curr_month_end = curr_month_start.replace(day=last_day, hour=23, minute=59, second=59)

    if now.month == 1:
        prev_year, prev_month = now.year - 1, 12
    else:
        prev_year, prev_month = now.year, now.month - 1

    prev_month_start = curr_month_start.replace(year=prev_year, month=prev_month, day=1)
    prev_last_day = calendar.monthrange(prev_year, prev_month)[1]
    prev_month_end = prev_month_start.replace(day=prev_last_day, hour=23, minute=59, second=59)

    curr_query = select(func.sum(Invoice.total)).where(
        Invoice.business_id == business_id,
        Invoice.status == InvoiceStatus.PAID,
        Invoice.created_at >= curr_month_start,
        Invoice.created_at <= curr_month_end,
    )
    curr_result = await db.execute(curr_query)
    current_month_revenue = float(curr_result.scalar() or 0)

    prev_query = select(func.sum(Invoice.total)).where(
        Invoice.business_id == business_id,
        Invoice.status == InvoiceStatus.PAID,
        Invoice.created_at >= prev_month_start,
        Invoice.created_at <= prev_month_end,
    )
    prev_result = await db.execute(prev_query)
    last_month_revenue = float(prev_result.scalar() or 0)

    if last_month_revenue > 0:
        pct_change = round(
            ((current_month_revenue - last_month_revenue) / last_month_revenue) * 100, 2
        )
    else:
        pct_change = 100.0 if current_month_revenue > 0 else 0.0

    res = {
        "currentMonth": calendar.month_name[now.month],
        "currentMonthRevenue": current_month_revenue,
        "lastMonth": calendar.month_name[prev_month],
        "lastMonthRevenue": last_month_revenue,
        "percentageChange": pct_change,
    }
    _set_cache(cache_key, res)
    return res


async def top_selling_products(
    db: AsyncSession,
    current_user_id: int,
    business_id: int,
    limit: int = 5,
    days: int = 30,
) -> list[dict]:
    await _get_authorized_business(db, current_user_id, business_id)

    cache_key = f"dashboard:{business_id}:top_products:{limit}:{days}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            Product.id,
            Product.name,
            Product.selling_price,
            func.sum(InvoiceItem.quantity).label("total_qty"),
            func.sum(InvoiceItem.quantity * Product.selling_price).label("total_revenue"),
        )
        .join(InvoiceItem, InvoiceItem.product_id == Product.id)
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .where(
            Invoice.business_id == business_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.created_at >= since,
        )
        .group_by(Product.id, Product.name, Product.selling_price)
        .order_by(func.sum(InvoiceItem.quantity).desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    res = [
        {
            "productId": r.id,
            "name": r.name,
            "sellingPrice": float(r.selling_price),
            "totalQty": int(r.total_qty),
            "totalRevenue": float(r.total_revenue),
        }
        for r in rows
    ]
    _set_cache(cache_key, res)
    return res


async def low_stock_products(
    db: AsyncSession,
    current_user_id: int,
    business_id: int,
    threshold: int = 10,
) -> list[dict]:
    await _get_authorized_business(db, current_user_id, business_id)

    cache_key = f"dashboard:{business_id}:low_stock:{threshold}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    query = (
        select(Product.id, Product.name, Product.stock, Product.category)
        .where(
            Product.business_id == business_id,
            Product.stock <= threshold,
        )
        .order_by(Product.stock.asc())
    )
    result = await db.execute(query)
    rows = result.all()

    res = [
        {
            "productId": r.id,
            "name": r.name,
            "stock": r.stock,
            "category": r.category,
        }
        for r in rows
    ]
    _set_cache(cache_key, res)
    return res


async def daily_revenue_trend(
    db: AsyncSession,
    current_user_id: int,
    business_id: int,
    days: int = 30,
) -> list[dict]:
    await _get_authorized_business(db, current_user_id, business_id)

    cache_key = f"dashboard:{business_id}:revenue_trend:{days}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            cast(Invoice.created_at, Date).label("date"),
            func.sum(Invoice.total).label("revenue"),
            func.count(Invoice.id).label("invoices"),
        )
        .where(
            Invoice.business_id == business_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.created_at >= since,
        )
        .group_by(cast(Invoice.created_at, Date))
        .order_by(cast(Invoice.created_at, Date))
    )
    result = await db.execute(query)
    rows = result.all()

    res = [
        {
            "date": str(r.date),
            "revenue": float(r.revenue),
            "invoices": int(r.invoices),
        }
        for r in rows
    ]
    _set_cache(cache_key, res)
    return res


async def invoice_status_breakdown(
    db: AsyncSession,
    current_user_id: int,
    business_id: int,
) -> dict:
    await _get_authorized_business(db, current_user_id, business_id)

    cache_key = f"dashboard:{business_id}:invoice_breakdown"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    query = (
        select(
            Invoice.status,
            func.count(Invoice.id).label("count"),
            func.coalesce(func.sum(Invoice.total), 0).label("amount"),
        )
        .where(Invoice.business_id == business_id)
        .group_by(Invoice.status)
    )
    result = await db.execute(query)
    rows = result.all()

    breakdown = {}
    for r in rows:
        breakdown[r.status.value] = {
            "count": int(r.count),
            "amount": float(r.amount),
        }

    for s in InvoiceStatus:
        if s.value not in breakdown:
            breakdown[s.value] = {"count": 0, "amount": 0.0}

    _set_cache(cache_key, breakdown)
    return breakdown


async def average_order_value(
    db: AsyncSession,
    current_user_id: int,
    business_id: int,
    days: int = 30,
) -> dict:
    await _get_authorized_business(db, current_user_id, business_id)

    cache_key = f"dashboard:{business_id}:avg_order_value:{days}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            func.avg(Invoice.total).label("avg_value"),
            func.min(Invoice.total).label("min_value"),
            func.max(Invoice.total).label("max_value"),
            func.count(Invoice.id).label("order_count"),
        )
        .where(
            Invoice.business_id == business_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.created_at >= since,
        )
    )
    result = await db.execute(query)
    row = result.one()

    res = {
        "averageOrderValue": round(float(row.avg_value or 0), 2),
        "minOrderValue": float(row.min_value or 0),
        "maxOrderValue": float(row.max_value or 0),
        "orderCount": int(row.order_count),
    }
    _set_cache(cache_key, res)
    return res


async def top_customers(
    db: AsyncSession,
    current_user_id: int,
    business_id: int,
    limit: int = 5,
    days: int = 90,
) -> list[dict]:
    await _get_authorized_business(db, current_user_id, business_id)

    cache_key = f"dashboard:{business_id}:top_customers:{limit}:{days}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            Customer.id,
            Customer.name,
            Customer.phone_number,
            func.sum(Invoice.total).label("total_spent"),
            func.count(Invoice.id).label("order_count"),
        )
        .join(Invoice, Invoice.customer_id == Customer.id)
        .where(
            Invoice.business_id == business_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.created_at >= since,
        )
        .group_by(Customer.id, Customer.name, Customer.phone_number)
        .order_by(func.sum(Invoice.total).desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    res = [
        {
            "customerId": r.id,
            "name": r.name,
            "phone": r.phone_number,
            "totalSpent": float(r.total_spent),
            "orderCount": int(r.order_count),
        }
        for r in rows
    ]
    _set_cache(cache_key, res)
    return res


async def profit_margins(
    db: AsyncSession,
    current_user_id: int,
    business_id: int,
    days: int = 30,
) -> dict:
    await _get_authorized_business(db, current_user_id, business_id)

    cache_key = f"dashboard:{business_id}:profit_margins:{days}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return cached

    since = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            func.sum(InvoiceItem.quantity * Product.selling_price).label("total_revenue"),
            func.sum(InvoiceItem.quantity * Product.original_price).label("total_cost"),
            func.sum(
                InvoiceItem.quantity * (Product.selling_price - Product.original_price)
            ).label("total_profit"),
        )
        .select_from(InvoiceItem)
        .join(Product, InvoiceItem.product_id == Product.id)
        .join(Invoice, Invoice.id == InvoiceItem.invoice_id)
        .where(
            Invoice.business_id == business_id,
            Invoice.status == InvoiceStatus.PAID,
            Invoice.created_at >= since,
        )
    )
    result = await db.execute(query)
    row = result.one()

    total_revenue = float(row.total_revenue or 0)
    total_cost = float(row.total_cost or 0)
    total_profit = float(row.total_profit or 0)
    margin_pct = round((total_profit / total_revenue) * 100, 2) if total_revenue > 0 else 0.0

    res = {
        "totalRevenue": total_revenue,
        "totalCost": total_cost,
        "totalProfit": total_profit,
        "marginPercent": margin_pct,
    }
    _set_cache(cache_key, res)
    return res

