from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

class CategoryEnum(str, Enum):
    MEAT = "MEAT"
    SAUSAGES = "SAUSAGES"
    LEGUMES = "LEGUMES"
    VEGETABLES = "VEGETABLES"
    STORE = "STORE"
    DISPOSABLE = "DISPOSABLE"
    OTHER = "OTHER"

class IngredientBase(BaseModel):
    name: str
    unit_price: float = Field(..., ge=0.0)
    unit: Optional[str] = "kg"
    category: CategoryEnum

class IngredientCreate(IngredientBase):
    pass

class IngredientUpdate(BaseModel):
    name: Optional[str] = None
    unit_price: Optional[float] = None
    unit: Optional[str] = None
    category: Optional[CategoryEnum] = None

class IngredientRead(IngredientBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class IngredientListResponse(BaseModel):
    items: List[IngredientRead]
    total: int
    limit: int
    offset: int
    next_offset: Optional[int] = None
    prev_offset: Optional[int] = None

    model_config = {"from_attributes": True}