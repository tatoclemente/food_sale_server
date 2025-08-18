# schemas/purchase.py
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from models.sale import PaymentStatus # pylint: disable=import-error

class PurchaseBase(BaseModel):
    ingredient_id: int
    quantity: float = Field(..., ge=0.0)
    unit_price: float = Field(..., ge=0.0)
    payment_status: PaymentStatus = Field(
        default=PaymentStatus.PENDING, description="Estado del pago"
    )
    supplier: Optional[str] = None
    notes: Optional[str] = None

class PurchaseCreate(PurchaseBase):
    purchased_at: Optional[datetime] = None  # si no viene, DB usa now()

class PurchaseUpdate(BaseModel):
    ingredient_id: Optional[int] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    supplier: Optional[str] = None
    notes: Optional[str] = None
    purchased_at: Optional[datetime] = None

class PurchaseRead(PurchaseBase):
    id: int
    total_amount: float
    purchased_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class PurchaseListResponse(BaseModel):
    items: List[PurchaseRead]
    total: int
    limit: int
    offset: int
    next_offset: Optional[int] = None
    prev_offset: Optional[int] = None

    model_config = {"from_attributes": True}
