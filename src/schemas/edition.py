from enum import Enum
import datetime as datetime_first
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator

# from schemas.edition_ingredient import EditionIngredientRead # pylint: disable=import-error

class EditionStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"

# -----------------------
# Base (validaciones comunes)
# -----------------------
class EditionBase(BaseModel):
    date: datetime_first.date = Field(..., description="Fecha de la edición (YYYY-MM-DD)")
    name: str = Field(..., min_length=1, description="Nombre de la edición (ej. 'Locro Agosto 2025')")
    portion_price: float = Field(..., ge=0, description="Precio por porción (>= 0)")
    notes: Optional[str] = Field(None, description="Notas opcionales")
    status: EditionStatus = Field(EditionStatus.PENDING, description="Estado de la edición")

    # Permite aceptar strings ISO (ej. '2025-08-01') o objetos date
    @field_validator("date", mode="before")
    def parse_date(cls, v): # pylint: disable=no-self-argument
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError:
                raise ValueError("date debe estar en formato ISO YYYY-MM-DD")
        if isinstance(v, date):
            return v
        raise ValueError("date debe ser date o string ISO YYYY-MM-DD")


# -----------------------
# Creación (POST)
# -----------------------
class EditionCreate(EditionBase):
    pass


# -----------------------
# Actualización parcial (PATCH)
# -----------------------
class EditionUpdate(BaseModel):
    date: Optional[datetime_first.date] = None
    name: Optional[str] = Field(None, min_length=1)
    portion_price: Optional[float] = Field(None, ge=0)
    notes: Optional[str] = None
    status: Optional[EditionStatus] = None 
    
    @field_validator("date", mode="before")
    def parse_date(cls, v): # pylint: disable=no-self-argument
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return date.fromisoformat(v)
            except ValueError:
                raise ValueError("date debe estar en formato ISO YYYY-MM-DD")
        return v


# -----------------------
# Read / Response model
# -----------------------
class EditionRead(EditionBase):
    id: int
    created_at: Optional[datetime] = None
    # Campo conveniente para dashboard (opcional)
    sales_count: Optional[int] = None
    edition_costs: float = 0.0          # <-- default 0.0
    net_profits: Optional[float] = None
    model_config = {"from_attributes": True}
    
class EditionListResponse(BaseModel):
    items: List[EditionRead]
    total: int
    limit: int
    offset: int
    next_offset: Optional[int] = None
    prev_offset: Optional[int] = None

# -----------------------
# Nota: si querés incluir la lista de ventas (SaleRead) dentro del EditionRead,
# podés hacerlo así (cuidado con imports circulares):
#
# from typing import List
# from .sale_schemas import SaleRead
#
# class EditionRead(EditionBase):
#     id: int
#     sales: List[SaleRead] = []
#     ...
#
# Asegurate de importar SaleRead de manera que no genere circular imports (por ejemplo,
# importarlo dentro de la función/endpoint o usar ForwardRef).
# -----------------------
