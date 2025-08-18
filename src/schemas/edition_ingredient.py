from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

# usamos previews ligeros para evitar importaciones circulares
from models.ingredient import Category  # pylint: disable=import-error
from schemas.preview import EditionPreview, IngredientPreview, PurchasePreview  # pylint: disable=import-error

class CategoryTotal(BaseModel):
    category: Category
    total: float

    model_config = {"from_attributes": True}
    
class EditionIngredientBase(BaseModel):
    ingredient_id: int
    quantity: float = Field(..., ge=0.0)
    notes: Optional[str] = None

class EditionIngredientCreate(EditionIngredientBase):
    unit_price: Optional[float] = None  # opcional si tu flujo rellena desde purchase/ingredient

class EditionIngredientUpdate(BaseModel):
    ingredient_id: Optional[int] = None
    quantity: Optional[float] = None
    notes: Optional[str] = None
    unit_price: Optional[float] = None

class EditionIngredientRead(EditionIngredientBase):
    id: int
    subtotal: float
    unit_price: float = Field(..., ge=0.0)
    created_at: Optional[datetime] = None

    # usamos previews para romper ciclos y mantener payloads razonables
    ingredient: Optional[IngredientPreview] = None
    edition: Optional[EditionPreview] = None
    # exposición de la compra asociada (si existe)
    purchase: Optional[PurchasePreview] = None

    model_config = {"from_attributes": True}

class EditionIngredientListResponse(BaseModel):
    items: List[EditionIngredientRead]
    total: int
    limit: int
    offset: int
    next_offset: Optional[int] = None
    prev_offset: Optional[int] = None

    category_totals: List[CategoryTotal] = []
    ingredients_total: float = 0.0
    total_expenses: Optional[float] = None 
    
    model_config = {"from_attributes": True}
