from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field

from schemas.customer import CustomerRead  # pylint: disable=import-error
from schemas.edition import EditionRead  # pylint: disable=import-error


class PaymentStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"


class SaleBase(BaseModel):
    total_portions: int = Field(..., ge=0, description="Cantidad total de porciones")
    payment_status: PaymentStatus = Field(
        default=PaymentStatus.PENDING, description="Estado del pago"
    )
    payment_transfer: bool = False
    delivered: bool = False
    saved: bool = False
    additional_cost: Optional[float] = Field(None, ge=0)
    sold_by: Optional[int] = None
    seller_name: Optional[str] = None
    discount_price: Optional[float] = Field(None, ge=0)
    customer_id: int


class SaleCreate(SaleBase):
    edition_id: int


# Para actualizaciones parciales (todos opcionales)
class SaleUpdate(BaseModel):
    total_amount: Optional[float] = Field(None, ge=0)
    total_portions: Optional[int] = Field(None, ge=0)
    payment_status: Optional[PaymentStatus] = None
    payment_transfer: Optional[bool] = None
    delivered: Optional[bool] = None
    saved: Optional[bool] = None
    additional_cost: Optional[float] = Field(None, ge=0)
    sold_by: Optional[int] = None
    seller_name: Optional[str] = None
    discount_price: Optional[float] = Field(None, ge=0)
    customer_id: Optional[int] = None
    edition_id: Optional[int] = None


# Modelo que devuelve la API (read)
class SaleRead(SaleBase):
    id: int
    total_amount: float
    edition_id: int
    created_at: Optional[datetime] = None
    
    customer: CustomerRead
    edition: EditionRead

    model_config = {"from_attributes": True}


# 📦 Respuesta con paginación
class SaleListResponse(BaseModel):
    items: List[SaleRead]
    total: int
    limit: int
    offset: int
    next_offset: Optional[int] = None
    prev_offset: Optional[int] = None
