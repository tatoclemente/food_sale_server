from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_db # pylint: disable=import-error
from crud import sale as crud_sale # pylint: disable=import-error
from schemas.sale import SaleCreate, SaleRead, SaleUpdate, SaleListResponse # pylint: disable=import-error

router = APIRouter()


@router.get("/", response_model=SaleListResponse, summary="Listar ventas")
def list_sales(
    limit: int = Query(100, ge=1, le=1000, description="Máximo resultados a devolver"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: Session = Depends(get_db),
):
    return crud_sale.get_sales(db=db, limit=limit, offset=offset)

@router.get("/edition/{edition_id}", response_model=SaleListResponse, summary="Listar ventas por edición")
def list_sales_edition(
    edition_id: int,
    customer_q: Optional[str] = Query(None, description="Buscar por nombre del cliente (ILIKE)"),
    payment_status: Optional[str] = Query(None, description="Estado de pago: PENDING|PAID"),
    payment_transfer: Optional[bool] = Query(None, description="Filtro por pago por transferencia"),
    delivered: Optional[bool] = Query(None, description="Filtro por entregado"),
    delivery: Optional[bool] = Query(None, description="Filtro por delivery"),
    freeze: Optional[bool] = Query(None, description="Filtro por congelado"),
    saved: Optional[bool] = Query(None, description="Filtro por guardado"),
    limit: int = Query(100, ge=1, le=1000, description="Máximo resultados a devolver"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: Session = Depends(get_db),
):
    return crud_sale.get_sales_edition(
        db=db,
        edition_id=edition_id,
        customer_q=customer_q,
        payment_status=payment_status,
        payment_transfer=payment_transfer,
        delivered=delivered,
        delivery=delivery,
        freeze=freeze,
        saved=saved,
        limit=limit,
        offset=offset,
    )
@router.get("/{sale_id}", response_model=SaleRead, summary="Obtener venta por id")
def get_sale(sale_id: int, db: Session = Depends(get_db)):
    # El CRUD ya lanza HTTPException(404) si no existe
    return crud_sale.get_sale(db, sale_id)


@router.post("/", response_model=SaleRead, status_code=status.HTTP_201_CREATED, summary="Crear venta")
def create_sale(payload: SaleCreate, db: Session = Depends(get_db)):
    sale = crud_sale.create_sale(db, payload)
    return sale


@router.patch("/{sale_id}", response_model=SaleRead, summary="Actualizar venta parcialmente")
def patch_sale(sale_id: int, payload: SaleUpdate, db: Session = Depends(get_db)):
    updated = crud_sale.update_sale(db, sale_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Sale not found")
    return updated


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar venta")
def delete_sale(sale_id: int, db: Session = Depends(get_db)): # pylint: disable=useless-return
    deleted = crud_sale.delete_sale(db, sale_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sale not found")
    return None
