from pydantic import BaseModel, Field, ConfigDict
from typing import Annotated, Optional
from datetime import datetime
from decimal import Decimal


class ProductBase(BaseModel):
    name: Annotated[str, Field(description='Product Name', examples=['Milk', 'Biscuit'], min_length=2, max_length=50)]
    original_price: Annotated[Decimal, Field(gt=0, description='MRP of Product', examples=[57, 121])]
    selling_price: Annotated[Decimal, Field(gt=0, description='Selling Price', examples=[49, 115])]
    stock: Annotated[int, Field(ge=0, description='Stock count', examples=[0, 10])]
    category: Annotated[Optional[str], Field(description='Category of Product', min_length=2, max_length=100)] = None
    sku: Annotated[Optional[str], Field(description='SKU of Product', max_length=50)] = None
    barcode: Annotated[Optional[str], Field(description='Barcode of Product', max_length=100)] = None
    description: Annotated[Optional[str], Field(description='Product description', max_length=500)] = None


class ProductCreate(ProductBase):
    business_id: int


class ProductUpdate(BaseModel):
    name: Annotated[Optional[str], Field(min_length=2, max_length=50)] = None
    original_price: Annotated[Optional[Decimal], Field(gt=0)] = None
    selling_price: Annotated[Optional[Decimal], Field(gt=0)] = None
    stock: Annotated[Optional[int], Field(ge=0)] = None
    category: Annotated[Optional[str], Field(min_length=2, max_length=100)] = None
    sku: Annotated[Optional[str], Field(max_length=50)] = None
    barcode: Annotated[Optional[str], Field(max_length=100)] = None
    description: Annotated[Optional[str], Field(max_length=500)] = None


class ProductOut(ProductBase):
    id: int
    business_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedProducts(BaseModel):
    items: list[ProductOut]
    total: int
    page: int
    limit: int

