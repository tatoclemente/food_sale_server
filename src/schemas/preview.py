from typing import Optional
from pydantic import BaseModel
from datetime import datetime

from models.ingredient import Category # pylint: disable=import-error
from models.purchase import PaymentStatus # pylint: disable=import-error

# Previews ligeros para romper ciclos entre esquemas grandes

class IngredientPreview(BaseModel):
    id: int
    name: Optional[str] = None
    category: Optional[Category] = None

    model_config = {"from_attributes": True}

class EditionPreview(BaseModel):
    id: int
    name: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

class PurchasePreview(BaseModel):
    id: int
    ingredient_id: int
    quantity: float
    unit_price: float
    total_amount: float
    purchased_at: Optional[datetime] = None
    payment_status: Optional[PaymentStatus] = None

    model_config = {"from_attributes": True}

class EditionIngredientPreview(BaseModel):
    id: int
    ingredient_id: int
    quantity: float
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}
