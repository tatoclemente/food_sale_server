import logging
from typing import Optional
from sqlalchemy import or_, func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from fastapi import HTTPException, status

from models.purchase import Purchase  # pylint: disable=import-error
from schemas.purchase import (  # pylint: disable=import-error
    PurchaseCreate,
    PurchaseListResponse,
    PurchaseRead,
    PurchaseUpdate,
)

logger = logging.getLogger(__name__)


def get_purchases(
    db: Session,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> PurchaseListResponse:
    """
    Búsqueda con paginación (limit/offset) y total.
    Retorna dict con keys: items, total, limit, offset, next_offset, prev_offset
    """
    try:
        stmt = select(Purchase)
        if q:
            term = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Purchase.supplier.ilike(term),
                    Purchase.notes.ilike(term)
                )
            )

        # total
        count_stmt = select(func.count()).select_from(stmt.subquery())  # pylint: disable=not-callable
        total = db.execute(count_stmt).scalar_one()

        # filas
        rows_stmt = stmt.order_by(Purchase.purchased_at.desc()).offset(offset).limit(limit)
        rows = db.execute(rows_stmt).scalars().all()

        items = [PurchaseRead.model_validate(r) for r in rows]

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
        logger.exception("Error al listar purchases con búsqueda=%s", q)
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al listar compras"
        )


def get_purchase(db: Session, purchase_id: int):
    purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return PurchaseRead.model_validate(purchase)


def create_purchase(db: Session, purchase: PurchaseCreate):
    payload = purchase.model_dump(exclude_none=True)
    db_purchase = Purchase(**payload)
    db.add(db_purchase)
    try:
        db.commit()
        db.refresh(db_purchase)
        return PurchaseRead.model_validate(db_purchase)
    except IntegrityError:
        db.rollback()
        logger.exception("Error de integridad al crear purchase")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad en los datos de la compra"
        )


def update_purchase(db: Session, purchase_id: int, purchase: PurchaseUpdate):
    db_purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if db_purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found")

    update_data = purchase.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_purchase, key, value)

    db.commit()
    db.refresh(db_purchase)
    return PurchaseRead.model_validate(db_purchase)


def delete_purchase(db: Session, purchase_id: int):
    db_purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
    if db_purchase is None:
        raise HTTPException(status_code=404, detail="Purchase not found")

    db.delete(db_purchase)
    db.commit()
    return PurchaseRead.model_validate(db_purchase)
