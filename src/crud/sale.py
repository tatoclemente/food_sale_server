import logging
from typing import Any, Dict, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from fastapi import HTTPException, status
from models.sale import Sale # pylint: disable=import-error
from models.edition import Edition # pylint: disable=import-error
from models.customer import Customer # pylint: disable=import-error
from schemas.sale import SaleCreate, SaleUpdate, SaleRead # pylint: disable=import-error

logger = logging.getLogger(__name__)

def _compute_total_amount(
    portions: int, 
    edition_price: float, 
    discount: Optional[float], 
    additional_cost: Optional[float]
) -> float:
    base = portions * edition_price
    discount_val = discount or 0.0
    add_cost = additional_cost or 0.0
    total = base - discount_val + add_cost
    if total < 0:
        total = 0.0
    # Redondear a 2 decimales (asegurate que tu DB almacene con precisión adecuada)
    return round(total, 2)

def get_sales(
    db: Session,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Listar ventas con paginación.
    Retorna dict con keys: items, total, limit, offset, next_offset, prev_offset
    """
    try:
        stmt = select(Sale)

        # Total de registros
        count_stmt = select(func.count()).select_from(stmt.subquery())  # pylint: disable=not-callable
        total = db.execute(count_stmt).scalar_one()

        # Filas con limit/offset
        rows_stmt = stmt.order_by(Sale.created_at.desc()).offset(offset).limit(limit)
        rows = db.execute(rows_stmt).scalars().all()

        items = [SaleRead.model_validate(r) for r in rows]

        next_offset = offset + limit if (offset + limit) < total else None
        prev_offset = offset - limit if (offset - limit) >= 0 else None

        return {
            "items": items,
            "total": int(total),
            "limit": limit,
            "offset": offset,
            "next_offset": next_offset,
            "prev_offset": prev_offset,
        }
    except SQLAlchemyError:
        logger.exception("Error al listar ventas")
        raise HTTPException(status_code=500, detail="Error de base de datos al listar ventas")


def get_sale(db: Session, sale_id: int):
    sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    return SaleRead(**sale.__dict__)


def create_sale(db: Session, sale: SaleCreate):
    # 1) validar existencia de edition y customer
    edition = db.query(Edition).filter(Edition.id == sale.edition_id).first()
    if edition is None:
        raise HTTPException(status_code=404, detail="Edition not found")

    customer = db.query(Customer).filter(Customer.id == sale.customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    if sale.total_portions < 0:
        raise HTTPException(status_code=400, detail="total_portions debe ser >= 0")

    # 2) calcular total en backend (ignorar lo que envía el cliente)
    total_amount = _compute_total_amount(
        portions=sale.total_portions,
        edition_price=edition.portion_price,
        discount=sale.discount_price,
        additional_cost=sale.additional_cost
    )

    # 3) crear objeto DB — sobreescribimos total_amount
    payload = sale.model_dump(exclude={"total_amount"})
    payload["total_amount"] = total_amount

    db_sale = Sale(**payload)
    db.add(db_sale)
    try:
        db.commit()
        db.refresh(db_sale)
        return SaleRead.model_validate(db_sale)
    except IntegrityError:
        db.rollback()
        logger.exception("Integrity error creando venta")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error de integridad al crear la venta")




def update_sale(db: Session, sale_id: int, sale: SaleUpdate):
    db_sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if db_sale is None:
        return None

    update_data = sale.model_dump(exclude_unset=True)

    # Si cambian campos que afectan el total (edition_id, total_portions, discount_price, additional_cost)
    recompute_needed = any(k in update_data for k in ("edition_id", "total_portions", "discount_price", "additional_cost"))

    # Aplicar cambios provisionales para calcular sobre el estado resultante
    # (no commit todavía)
    for key, value in update_data.items():
        setattr(db_sale, key, value)

    if recompute_needed:
        # obtener edition actual (posible que hayan actualizado edition_id)
        edition_id = getattr(db_sale, "edition_id")
        edition = db.query(Edition).filter(Edition.id == edition_id).first()
        if edition is None:
            raise HTTPException(status_code=404, detail="Edition not found")

        portions = getattr(db_sale, "total_portions", 0)
        discount = getattr(db_sale, "discount_price", None)
        add_cost = getattr(db_sale, "additional_cost", None)

        total_amount = _compute_total_amount(portions, edition.portion_price, discount, add_cost)
        db_sale.total_amount = total_amount

    try:
        db.commit()
        db.refresh(db_sale)
        return SaleRead.model_validate(db_sale)
    except IntegrityError:
        db.rollback()
        logger.exception("Integrity error actualizando venta")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Error de integridad al actualizar la venta")

def delete_sale(db: Session, sale_id: int):
    db_sale = db.query(Sale).filter(Sale.id == sale_id).first()
    if db_sale is None:
        return None

    db.delete(db_sale)
    db.commit()
    return db_sale
