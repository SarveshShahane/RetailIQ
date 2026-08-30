import json
import os
import re
from decimal import Decimal, ROUND_HALF_UP

import httpx

from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from models.invoice import Customer, Invoice, InvoiceItem, InvoiceSource, InvoiceStatus
from models.products import Product
from models.user import Business
from services.products import _get_business_for_user
from services.analytics import invalidate_dashboard_cache
from schemas.invoice import (
	InvoiceCreatePayload,
	InvoiceMetadata,
	InvoiceUpdate,
)
from exceptions.business import BusinessException, BusinessNotFoundException, UnauthorisedBusinessAccess
from exceptions.database import DatabaseIntegrityException, DatabaseUnexpectedException
from exceptions.invoice import InvoiceException, InvoiceNotFoundException, InvalidInvoiceException, InsufficientStockException


MONEY_QUANT = Decimal("0.01")



def _to_decimal(value: Decimal | int | float | str | None) -> Decimal | None:
	if value is None:
		return None
	if isinstance(value, Decimal):
		return value
	return Decimal(str(value))


def _quantize_money(value: Decimal) -> Decimal:
	return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


async def _resolve_customer(
	db: AsyncSession,
	business_id: int,
	payload: InvoiceCreatePayload,
) -> int | None:
	if payload.customer_id:
		return payload.customer_id

	if not payload.customer:
		return None

	if not payload.customer.phone_number:
		raise InvalidInvoiceException(
			"Customer phone number is required to create a new customer"
		)

	filters = []
	if payload.customer.phone_number:
		filters.append(Customer.phone_number == payload.customer.phone_number)
	if payload.customer.email:
		filters.append(Customer.email == payload.customer.email)

	result = await db.execute(
		select(Customer)
		.where(Customer.business_id == business_id)
		.where(or_(*filters))
	)
	existing = result.scalars().first()
	if existing:
		return existing.id

	customer = Customer(
		business_id=business_id,
		name=payload.customer.name,
		phone_number=payload.customer.phone_number,
		email=payload.customer.email,
	)
	db.add(customer)
	await db.flush()
	return customer.id


async def _resolve_product(
	db: AsyncSession,
	business_id: int,
	product_id: int | None,
	sku: str | None,
	barcode: str | None,
) -> Product:
	if product_id is not None:
		result = await db.execute(
			select(Product).where(
				Product.id == product_id,
				Product.business_id == business_id,
			)
		)
		product = result.scalar_one_or_none()
		if not product:
			raise InvalidInvoiceException(f"Invalid product_id {product_id}")
		return product

	if not sku and not barcode:
		raise InvalidInvoiceException("Each item must include product_id, sku, or barcode")

	query = select(Product).where(Product.business_id == business_id)
	filters = []
	if sku:
		filters.append(Product.sku == sku)
	if barcode:
		filters.append(Product.barcode == barcode)
	result = await db.execute(query.where(or_(*filters)))
	product = result.scalars().first()
	if not product:
		raise InvalidInvoiceException("No matching product found for sku/barcode")
	return product


def _calculate_totals(
	payload: InvoiceCreatePayload,
	items: list[tuple[Product, int]],
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
	subtotal = Decimal("0")
	for product, quantity in items:
		subtotal += _to_decimal(product.selling_price) * Decimal(quantity)
	subtotal = _quantize_money(subtotal)

	tax = _quantize_money(_to_decimal(payload.tax or 0) or Decimal("0"))
	discount = _quantize_money(_to_decimal(payload.discount or 0) or Decimal("0"))
	total = _quantize_money(subtotal + tax - discount)

	if payload.subtotal is not None and _quantize_money(_to_decimal(payload.subtotal)) != subtotal:
		raise InvalidInvoiceException("Subtotal mismatch")
	if payload.total is not None and _quantize_money(_to_decimal(payload.total)) != total:
		raise InvalidInvoiceException("Total mismatch")

	return subtotal, tax, discount, total


async def create_invoice(
	db: AsyncSession,
	payload: InvoiceCreatePayload,
	current_user_id: int,
) -> Invoice:
	try:
		business = await _get_business_for_user(db, payload.business_id, current_user_id)

		customer_id = await _resolve_customer(db, payload.business_id, payload)

		resolved_items: list[tuple[Product, int]] = []
		for item in payload.items:
			product = await _resolve_product(
				db,
				payload.business_id,
				item.product_id,
				item.sku,
				item.barcode,
			)
			resolved_items.append((product, item.quantity))

		subtotal, tax, discount, total = _calculate_totals(payload, resolved_items)
		status_str = payload.status.value if hasattr(payload.status, "value") else payload.status
		source_str = payload.source.value if hasattr(payload.source, "value") else payload.source
		model_status = InvoiceStatus[status_str]
		model_source = InvoiceSource[source_str]

		invoice = Invoice(
			business_id=payload.business_id,
			customer_id=customer_id,
			payment_id=payload.payment_id,
			status=model_status,
			source=model_source,
			subtotal=subtotal,
			tax=tax,
			discount=discount,
			total=total,
			notes=payload.notes,
		)
		db.add(invoice)
		await db.flush()

		for product, quantity in resolved_items:
			invoice_item = InvoiceItem(
				invoice_id=invoice.id,
				product_id=product.id,
				quantity=quantity,
			)
			db.add(invoice_item)

			if model_status == InvoiceStatus.PAID:
				if product.stock < quantity:
					raise InsufficientStockException(
						f"Insufficient stock for product {product.id}"
					)
				product.stock -= quantity

		await db.commit()
		invalidate_dashboard_cache(invoice.business_id)
		result = await db.execute(
			select(Invoice)
			.options(
				selectinload(Invoice.items).selectinload(InvoiceItem.product),
				selectinload(Invoice.customer)
			)
			.where(Invoice.id == invoice.id)
		)
		invoice = result.scalar_one()
		return invoice
	except (InvoiceException, BusinessException) as exc:
		await db.rollback()
		raise exc
	except Exception as exc:
		await db.rollback()
		raise DatabaseUnexpectedException(
			f"An unexpected database error occurred while creating invoice: {str(exc)}"
		) from exc


async def get_invoice_by_id(
	db: AsyncSession,
	invoice_id: int,
	current_user_id: int,
) -> Invoice:
	try:
		result = await db.execute(
			select(Invoice)
			.options(
				selectinload(Invoice.items).selectinload(InvoiceItem.product),
				selectinload(Invoice.customer)
			)
			.where(Invoice.id == invoice_id)
		)
		invoice = result.scalar_one_or_none()
		if not invoice:
			raise InvoiceNotFoundException("Invalid invoice id")

		await _get_business_for_user(db, invoice.business_id, current_user_id)

		return invoice
	except (InvoiceException, BusinessException) as exc:
		raise exc
	except Exception as exc:
		raise DatabaseUnexpectedException(
			f"An unexpected database error occurred while fetching invoice: {str(exc)}"
		) from exc


async def get_invoice_metadata(
	db: AsyncSession,
	business_id: int,
	current_user_id: int,
) -> InvoiceMetadata:
	await _get_business_for_user(db, business_id, current_user_id)

	invoice_result = await db.execute(
		select(Invoice)
		.options(selectinload(Invoice.customer))
		.where(Invoice.business_id == business_id)
		.order_by(Invoice.created_at.desc())
	)
	invoice = invoice_result.scalar_one_or_none()
	if not invoice:
		raise InvoiceNotFoundException("No invoices found for this business")

	customer_name = invoice.customer.name if invoice.customer else "Walk-in"
	return InvoiceMetadata(
		customer_name=customer_name,
		status=invoice.status,
		tax=invoice.tax or 0,
		discount=invoice.discount or 0,
		total=invoice.total or 0,
	)


async def update_invoice(
	db: AsyncSession,
	invoice_id: int,
	payload: InvoiceUpdate,
	current_user_id: int,
) -> Invoice:
	try:
		invoice_result = await db.execute(
			select(Invoice)
			.options(
				selectinload(Invoice.items).selectinload(InvoiceItem.product),
				selectinload(Invoice.customer)
			)
			.where(Invoice.id == invoice_id)
		)
		invoice = invoice_result.scalar_one_or_none()
		if not invoice:
			raise InvoiceNotFoundException("Invalid invoice id")

		await _get_business_for_user(db, invoice.business_id, current_user_id)

		update_data = payload.model_dump(exclude_unset=True)

		old_status = invoice.status
		new_status = old_status
		if "status" in update_data and update_data["status"] is not None:
			status_val = update_data["status"].value if hasattr(update_data["status"], "value") else update_data["status"]
			new_status = InvoiceStatus[status_val]

		if old_status != new_status:
			stock_was_deducted_before = (old_status == InvoiceStatus.PAID)
			stock_should_be_deducted_now = (new_status == InvoiceStatus.PAID)

			if stock_should_be_deducted_now and not stock_was_deducted_before:
				for item in invoice.items:
					if item.product:
						if item.product.stock < item.quantity:
							raise InsufficientStockException(
								f"Insufficient stock for product '{item.product.name}' (ID: {item.product.id})"
							)
						item.product.stock -= item.quantity
			elif not stock_should_be_deducted_now and stock_was_deducted_before:
				for item in invoice.items:
					if item.product:
						item.product.stock += item.quantity

		for key, value in update_data.items():
			if key == "status":
				value = new_status
			setattr(invoice, key, value)

		await db.commit()
		invalidate_dashboard_cache(invoice.business_id)
		result = await db.execute(
			select(Invoice)
			.options(
				selectinload(Invoice.items).selectinload(InvoiceItem.product),
				selectinload(Invoice.customer)
			)
			.where(Invoice.id == invoice_id)
		)
		invoice = result.scalar_one()
		return invoice
	except (InvoiceException, BusinessException) as exc:
		await db.rollback()
		raise exc
	except Exception as exc:
		await db.rollback()
		raise DatabaseUnexpectedException(
			f"An unexpected database error occurred while updating invoice: {str(exc)}"
		) from exc


def _parse_money(value: str | None) -> Decimal | None:
	if not value:
		return None
	try:
		return Decimal(value.replace(",", ""))
	except Exception:
		return None





async def list_invoices(
	db: AsyncSession,
	business_id: int,
	current_user_id: int,
	page: int | None = None,
	limit: int | None = None,
) -> list[Invoice]:
	await _get_business_for_user(db, business_id, current_user_id)

	query = select(Invoice).options(
		selectinload(Invoice.items).selectinload(InvoiceItem.product),
		selectinload(Invoice.customer)
	).where(Invoice.business_id == business_id).order_by(Invoice.created_at.desc())

	if page is not None and limit is not None:
		query = query.offset((page - 1) * limit).limit(limit)

	result = await db.execute(query)
	return list(result.scalars().all())


async def count_invoices(
	db: AsyncSession,
	business_id: int,
) -> int:
	result = await db.execute(
		select(func.count(Invoice.id)).where(Invoice.business_id == business_id)
	)
	return result.scalar() or 0


async def list_customers(
	db: AsyncSession,
	business_id: int,
	current_user_id: int,
) -> list[Customer]:
	await _get_business_for_user(db, business_id, current_user_id)

	result = await db.execute(
		select(Customer)
		.where(Customer.business_id == business_id)
		.order_by(Customer.name.asc())
	)
	return list(result.scalars().all())