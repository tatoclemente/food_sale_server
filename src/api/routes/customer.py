from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db
from crud import customer as crud_customer
from schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate, CustomerListResponse

router = APIRouter()

@router.get("/", response_model=CustomerListResponse, summary="Listar clientes")
def list_customers(
    q: Optional[str] = Query(None, description="Término de búsqueda (nombre, email o teléfono)"),
    limit: int = Query(100, ge=1, le=1000, description="Máximo resultados a devolver"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: Session = Depends(get_db)
):
    return crud_customer.get_customers(db=db, q=q, limit=limit, offset=offset)


@router.get("/{customer_id}", response_model=CustomerRead, summary="Obtener cliente por id")
def get_customer(customer_id: int, db: Session = Depends(get_db)):
    # El CRUD ya lanza HTTPException(404) si no existe
    return crud_customer.get_customer(db, customer_id)


@router.post("/", response_model=CustomerRead, status_code=status.HTTP_201_CREATED, summary="Crear cliente")
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    # El CRUD maneja IntegrityError y convierte a HTTPException(409)
    customer = crud_customer.create_customer(db, payload)
    return customer


@router.patch("/{customer_id}", response_model=CustomerRead, summary="Actualizar cliente parcialmente")
def patch_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    updated = crud_customer.update_customer(db, customer_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Customer not found")
    return updated


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar cliente")
def delete_customer(customer_id: int, db: Session = Depends(get_db)): # pylint: disable=useless-return
    deleted = crud_customer.delete_customer(db, customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Customer not found")
    return None