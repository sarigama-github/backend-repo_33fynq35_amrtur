"""
Database Schemas for Coral Shopping

Each Pydantic model represents a collection in your MongoDB database.
Collection name is the lowercase of the class name (e.g., Product -> "product").
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime


class Customer(BaseModel):
    full_name: str = Field(..., description="Customer full name")
    email: EmailStr = Field(..., description="Customer email")
    phone: Optional[str] = Field(None, description="Nigerian phone number")
    addresses: Optional[List[str]] = Field(default_factory=list, description="Saved delivery addresses")
    balance: float = Field(0, ge=0, description="Account balance for credits/refunds")
    is_active: bool = Field(True)


class Product(BaseModel):
    title: str = Field(..., description="Product title")
    description: Optional[str] = Field(None)
    price: float = Field(..., ge=0, description="Price in Naira")
    category: Literal[
        'foodstuffs', 'gifts', 'hampers', 'household', 'office'
    ] = Field(..., description="Product category")
    images: Optional[List[str]] = Field(default_factory=list)
    in_stock: bool = Field(True)
    stock_qty: Optional[int] = Field(0, ge=0)
    tags: Optional[List[str]] = Field(default_factory=list)
    rating: Optional[float] = Field(0, ge=0, le=5)


class OrderItem(BaseModel):
    product_id: str = Field(...)
    title: str = Field(...)
    unit_price: float = Field(..., ge=0)
    quantity: int = Field(..., ge=1)


class Order(BaseModel):
    customer_id: str = Field(...)
    items: List[OrderItem] = Field(...)
    subtotal: float = Field(..., ge=0)
    shipping_fee: float = Field(0, ge=0)
    total: float = Field(..., ge=0)
    payment_method: Literal['bank_transfer'] = Field('bank_transfer')
    payment_status: Literal['pending', 'confirmed', 'failed'] = Field('pending')
    status: Literal['pending', 'processing', 'shipped', 'delivered', 'cancelled'] = Field('pending')
    delivery_option: Literal['pickup', 'delivery'] = Field('delivery')
    delivery_address: Optional[str] = None
    notes: Optional[str] = None


class SupportTicket(BaseModel):
    customer_id: str
    subject: str
    message: str
    status: Literal['open', 'in_progress', 'resolved'] = 'open'


# Minimal analytics event to measure recommendation effectiveness
class AnalyticsEvent(BaseModel):
    type: Literal['view', 'click', 'add_to_cart', 'purchase', 'recommendation_click']
    customer_id: Optional[str] = None
    product_id: Optional[str] = None
    meta: Optional[dict] = None
    timestamp: Optional[datetime] = None
