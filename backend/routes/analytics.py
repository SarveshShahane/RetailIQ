from fastapi import APIRouter, Depends, status, HTTPException
from middlewares.auth import current_user
from db.database import get_async_db
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum
from typing import Optional
from sqlalchemy import func, select
from models.invoice import Invoice, InvoiceStatus, Customer
from models.user import Business
from datetime import datetime, timedelta, timezone
from services.analytics import (
    numeric_analytics as numeric_analytics_service,
    total_revenue,
    top_selling_products,
    low_stock_products,
    daily_revenue_trend,
    invoice_status_breakdown,
    average_order_value,
    top_customers,
    profit_margins,
)

router = APIRouter(
    prefix='/dashboard',
    tags=['dashboard']
)

class Time(str, Enum):
    today = 'today'
    week = 'week'
    month = 'month'
    year = 'year'
    all = 'all'

@router.get('/')
async def numeric_analytics(
    business_id: int,
    time: Time = Time.month,
    current_user_id: int = Depends(current_user),
    db: AsyncSession = Depends(get_async_db)
):
    return await numeric_analytics_service(db, current_user_id, business_id, time.value)


@router.get('/revenue')
async def revenue_analytics(
    business_id: int,
    current_user_id: int = Depends(current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await total_revenue(db, current_user_id, business_id)


@router.get('/top-products')
async def top_products_analytics(
    business_id: int,
    limit: int = 5,
    days: int = 30,
    current_user_id: int = Depends(current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await top_selling_products(db, current_user_id, business_id, limit, days)


@router.get('/low-stock')
async def low_stock_analytics(
    business_id: int,
    threshold: int = 10,
    current_user_id: int = Depends(current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await low_stock_products(db, current_user_id, business_id, threshold)


@router.get('/revenue-trend')
async def revenue_trend_analytics(
    business_id: int,
    days: int = 30,
    current_user_id: int = Depends(current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await daily_revenue_trend(db, current_user_id, business_id, days)


@router.get('/invoice-breakdown')
async def invoice_breakdown_analytics(
    business_id: int,
    current_user_id: int = Depends(current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await invoice_status_breakdown(db, current_user_id, business_id)


@router.get('/avg-order-value')
async def avg_order_value_analytics(
    business_id: int,
    days: int = 30,
    current_user_id: int = Depends(current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await average_order_value(db, current_user_id, business_id, days)


@router.get('/top-customers')
async def top_customers_analytics(
    business_id: int,
    limit: int = 5,
    days: int = 90,
    current_user_id: int = Depends(current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await top_customers(db, current_user_id, business_id, limit, days)


@router.get('/profit-margins')
async def profit_margins_analytics(
    business_id: int,
    days: int = 30,
    current_user_id: int = Depends(current_user),
    db: AsyncSession = Depends(get_async_db),
):
    return await profit_margins(db, current_user_id, business_id, days)
