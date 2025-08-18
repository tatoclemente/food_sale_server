from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr

# -----------------------
# Esquema base (validaciones comunes)
# -----------------------
class CustomerBase(BaseModel):
    name: str = Field(..., min_length=1, description="Nombre completo del cliente")
    email: Optional[EmailStr] = Field(None, description="Email del cliente")
    phone: Optional[str] = Field(None, description="Teléfono (opcional)")
    address: Optional[str] = Field(None, description="Dirección (opcional)")

# -----------------------
# Para creación (POST)
# -----------------------
class CustomerCreate(CustomerBase):
    pass

# -----------------------
# Para actualizaciones parciales (PATCH)
# -----------------------
class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None

# -----------------------
# Modelo de lectura (respuesta de la API)
# -----------------------
class CustomerRead(CustomerBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = {
        "from_attributes": True
    }

class CustomerListResponse(BaseModel):
    items: List[CustomerRead]
    total: int
    limit: int
    offset: int
    next_offset: Optional[int] = None
    prev_offset: Optional[int] = None

    model_config = {"from_attributes": True}