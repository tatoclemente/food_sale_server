import logging
from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from fastapi import HTTPException, status
from models.sale import Sale # pylint: disable=import-error
from models.edition import Edition # pylint: disable=import-error
from models.customer import Customer # pylint: disable=import-error
from schemas.sale import SaleCreate, SaleListResponse, SaleUpdate, SaleRead # pylint: disable=import-error

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
) -> SaleListResponse:
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

def get_sales_edition(
    db: Session,
    edition_id: int,
    *,
    customer_q: Optional[str] = None,
    payment_status: Optional[str] = None,
    payment_transfer: Optional[bool] = None,
    delivered: Optional[bool] = None,
    delivery: Optional[bool] = None,
    freeze: Optional[bool] = None,
    saved: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
) -> SaleListResponse:
    """
    Listar ventas con paginación, filtradas por edition_id y opcionalmente por:
      - customer_q (nombre del cliente, buscado con ILIKE)
      - payment_status (string, ej. "PENDING" / "PAID")
      - payment_transfer (bool)
      - delivered (bool)
      - delivery (bool)
      - freeze (bool)
      - saved (bool)

    Retorna SaleListResponse (items, total, limit, offset, next_offset, prev_offset).
    """
    try:
        # base statement
        stmt = select(Sale)

        # filtro por edición (requerido)
        stmt = stmt.where(Sale.edition_id == edition_id)

        # filtro por nombre del cliente (usa la relación Customer)
        if customer_q:
            term = f"%{customer_q.strip()}%"
            # filtra usando existencia de customer con nombre coincidente
            stmt = stmt.where(Sale.customer.has(Customer.name.ilike(term)))

        # filtros directos por columnas
        if payment_status is not None:
            stmt = stmt.where(Sale.payment_status == payment_status)

        if payment_transfer is not None:
            stmt = stmt.where(Sale.payment_transfer == payment_transfer)

        if delivered is not None:
            stmt = stmt.where(Sale.delivered == delivered)

        if delivery is not None:
            stmt = stmt.where(Sale.delivery == delivery)

        if freeze is not None:
            stmt = stmt.where(Sale.freeze == freeze)

        if saved is not None:
            stmt = stmt.where(Sale.saved == saved)

        # total sobre la consulta filtrada
        count_stmt = select(func.count()).select_from(stmt.subquery())  # pylint: disable=not-callable
        total = db.execute(count_stmt).scalar_one()

        # traer filas (con las relaciones necesarias eager-loaded para pydantic)
        rows_stmt = (
            stmt
            .options(
                joinedload(Sale.customer),  # traer customer si SaleRead lo necesita
                joinedload(Sale.edition),
            )
            .order_by(Sale.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
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
        logger.exception(
            "Error al listar ventas para edition_id=%s customer_q=%s payment_status=%s payment_transfer=%s delivered=%s delivery=%s freeze=%s saved=%s",
            edition_id, customer_q, payment_status, payment_transfer, delivered, delivery, freeze, saved
        )
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

    # 1.1) validar portion_price si lo usas para calcular total
    if edition.portion_price is None:
        raise HTTPException(status_code=400, detail="La edición no tiene portion_price definido")

    # 2) validar business rules
    if sale.total_portions < 0:
        raise HTTPException(status_code=400, detail="total_portions debe ser >= 0")

    # 3) calcular total en backend (ignorar lo que envía el cliente)
    total_amount = _compute_total_amount(
        portions=sale.total_portions,
        edition_price=edition.portion_price,
        discount=sale.discount_price,
        additional_cost=sale.additional_cost
    )

    # 4) prevenir duplicados (UX) — aún así la constraint DB protege de race conditions
    existing = (
        db.query(Sale)
        .filter(Sale.edition_id == sale.edition_id, Sale.customer_id == sale.customer_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El cliente ya tiene una compra registrada para esta edición"
        )

    # 5) construir payload sobrescribiendo total_amount
    payload = sale.model_dump(exclude={"total_amount"})
    payload["total_amount"] = total_amount

    db_sale = Sale(**payload)
    db.add(db_sale)
    try:
        db.commit()
        db.refresh(db_sale)
        return SaleRead.model_validate(db_sale)
    except IntegrityError as exc:
        db.rollback()
        logger.exception("Integrity error creando venta: %s", exc)

        # intentar detectar duplicate key / unique violation
        orig = getattr(exc, "orig", None)
        msg = str(orig).lower() if orig is not None else str(exc).lower()
        if "uq_sale_edition_customer" in msg or "duplicate key" in msg or "unique constraint" in msg or "23505" in msg:
            # unique constraint fired -> conflicto
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El cliente ya tiene una compra registrada para esta edición (constraint)"
            )

        # otros errores de integridad
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
