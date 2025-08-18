from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db  # pylint: disable=import-error, unused-import
from crud import purchase as crud_purchase  # pylint: disable=import-error, unused-import
from schemas.purchase import (  # pylint: disable=import-error, unused-import
    PurchaseCreate,
    PurchaseRead,
    PurchaseListResponse,
    PurchaseUpdate,
)

router = APIRouter()


@router.get("/", response_model=PurchaseListResponse, summary="Listar compras")
def list_purchases(
    q: Optional[str] = Query(None, description="Término de búsqueda (supplier o notes)"),
    limit: int = Query(100, ge=1, le=1000, description="Máximo resultados a devolver"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: Session = Depends(get_db),
):
    return crud_purchase.get_purchases(db=db, q=q, limit=limit, offset=offset)


@router.get("/{purchase_id}", response_model=PurchaseRead, summary="Obtener compra por id")
def get_purchase(purchase_id: int, db: Session = Depends(get_db)):
    # El CRUD ya lanza HTTPException(404) si no existe
    return crud_purchase.get_purchase(db, purchase_id)


@router.post(
    "/",
    response_model=PurchaseRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear compra"
)
def create_purchase(payload: PurchaseCreate, db: Session = Depends(get_db)):
    purchase = crud_purchase.create_purchase(db, payload)
    return purchase


@router.patch(
    "/{purchase_id}",
    response_model=PurchaseRead,
    summary="Actualizar compra parcialmente"
)
def patch_purchase(purchase_id: int, payload: PurchaseUpdate, db: Session = Depends(get_db)):
    updated = crud_purchase.update_purchase(db, purchase_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return updated


@router.delete(
    "/{purchase_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar compra"
)
def delete_purchase(purchase_id: int, db: Session = Depends(get_db)):  # pylint: disable=useless-return
    deleted = crud_purchase.delete_purchase(db, purchase_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return None
