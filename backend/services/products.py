import json
from redis_client import redisClient
from sqlalchemy.exc import IntegrityError
from exceptions.pruduct import ProductNotFound
from exceptions.business import BusinessNotFoundException,UnauthorisedBusinessAccess
from exceptions.database import DatabaseIntegrityException, DatabaseUnexpectedException
from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.products import Product as ProductModel
from models.user import Business
from schemas.products import ProductCreate, ProductUpdate
from services.analytics import invalidate_dashboard_cache


async def _get_business_for_user(
	db: AsyncSession,
	business_id: int,
	current_user_id: int,
) -> Business:
	cache_key = f"business:{business_id}"
	
	import sys
	import os
	is_testing = "pytest" in sys.modules or "PYTEST_CURRENT_TEST" in os.environ

	if not is_testing:
		try:
			cached_business = redisClient.get(cache_key)
			if cached_business:
				business_data = json.loads(cached_business)
				if business_data.get("user_id") != current_user_id:
					raise UnauthorisedBusinessAccess()
				return Business(
					id=business_data.get("id"),
					user_id=business_data.get("user_id"),
					name=business_data.get("name")
				)
		except (UnauthorisedBusinessAccess, BusinessNotFoundException):
			raise
		except Exception as e:
			print(f"Redis cache read error: {e}")

	result = await db.execute(
		select(Business).where(Business.id == business_id)
	)
	business = result.scalar_one_or_none()
	if not business:
		raise BusinessNotFoundException()
	if current_user_id != business.user_id:
		raise UnauthorisedBusinessAccess()

	if not is_testing:
		try:
			redisClient.set(
				cache_key,
				json.dumps({
					"id": business.id,
					"user_id": business.user_id,
					"name": business.name
				}),
				ex=3600
			)
		except Exception as e:
			print(f"Redis cache write error: {e}")

	return business


async def list_products(
	db: AsyncSession,
	business_id: int,
	current_user_id: int,
	page: int | None = None,
	limit: int | None = None,
) -> list[ProductModel]:
	await _get_business_for_user(db, business_id, current_user_id)
	query = select(ProductModel).where(ProductModel.business_id == business_id)
	if page is not None and limit is not None:
		query = query.offset((page - 1) * limit).limit(limit)
	result = await db.execute(query)
	return result.scalars().all()


async def count_products(
	db: AsyncSession,
	business_id: int,
) -> int:
	result = await db.execute(
		select(func.count(ProductModel.id)).where(ProductModel.business_id == business_id)
	)
	return result.scalar() or 0


async def search_products(
	db: AsyncSession,
	business_id: int,
	sku: str | None,
	barcode: str | None,
	name: str | None,
	current_user_id: int,
) -> list[ProductModel]:
	await _get_business_for_user(db, business_id, current_user_id)
	query = select(ProductModel).where(ProductModel.business_id == business_id)
	filters = []
	if sku:
		filters.append(ProductModel.sku == sku)
	if barcode:
		filters.append(ProductModel.barcode == barcode)
	if name:
		filters.append(ProductModel.name.ilike(f"%{name}%"))
	if filters:
		query = query.where(or_(*filters))
	result = await db.execute(query)
	return result.scalars().all()


async def get_product_by_id(
	db: AsyncSession,
	product_id: int,
	current_user_id: int,
) -> ProductModel:
	result = await db.execute(
		select(ProductModel).where(ProductModel.id == product_id)
	)
	product = result.scalar_one_or_none()
	if not product:
		raise ProductNotFound()
	await _get_business_for_user(db, product.business_id, current_user_id)
	return product


async def create_product(
	db: AsyncSession,
	payload: ProductCreate,
	current_user_id: int,
) -> ProductModel:
	business = await _get_business_for_user(
		db,
		payload.business_id,
		current_user_id,
	)

	try:
		product = ProductModel(
			name=payload.name,
			business_id=business.id,
			original_price=payload.original_price,
			selling_price=payload.selling_price,
			stock=payload.stock,
			category=payload.category,
			sku=payload.sku,
			barcode=payload.barcode,
			description=payload.description,
		)
		db.add(product)
		await db.commit()
		invalidate_dashboard_cache(product.business_id)
		await db.refresh(product)
		return product
	except IntegrityError as exc:
		await db.rollback()
		raise DatabaseIntegrityException(
			"Database integrity violation while creating product."
		) from exc
	except Exception as exc:
		await db.rollback()
		raise DatabaseUnexpectedException(
			"An unexpected database error occurred while creating product."
		) from exc


async def update_product(
	db: AsyncSession,
	product_id: int,
	payload: ProductUpdate,
	current_user_id: int,
) -> ProductModel:
	result = await db.execute(
		select(ProductModel).where(ProductModel.id == product_id)
	)
	product = result.scalar_one_or_none()
	if not product:
		raise ProductNotFound()
	await _get_business_for_user(db, product.business_id, current_user_id)
	try:
		update_data = payload.model_dump(exclude_unset=True)
		for key, value in update_data.items():
			setattr(product, key, value)
		await db.commit()
		invalidate_dashboard_cache(product.business_id)
		await db.refresh(product)
		return product
	except IntegrityError as exc:
		await db.rollback()
		raise DatabaseIntegrityException(
			"Database integrity violation while updating product."
		) from exc
	except Exception as exc:
		await db.rollback()
		raise DatabaseUnexpectedException(
			"An unexpected database error occurred while updating product."
		) from exc


async def delete_product(
	db: AsyncSession,
	product_id: int,
	current_user_id: int,
) -> None:
	result = await db.execute(
		select(ProductModel).where(ProductModel.id == product_id)
	)
	product = result.scalar_one_or_none()
	if not product:
		raise ProductNotFound()
	await _get_business_for_user(db, product.business_id, current_user_id)
	try:
		business_id = product.business_id
		await db.delete(product)
		await db.commit()
		invalidate_dashboard_cache(business_id)
	except Exception as exc:
		await db.rollback()
		raise DatabaseUnexpectedException(
			"An unexpected database error occurred while deleting product."
		) from exc
