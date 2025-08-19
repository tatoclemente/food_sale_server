import logging
from typing import Optional
from sqlalchemy import or_, func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from fastapi import HTTPException, status

from models.edition import Edition # pylint: disable=import-error
from models.edition_ingredient import EditionIngredient # pylint: disable=import-error
from models.sale import Sale # pylint: disable=import-error
from schemas.edition import EditionCreate, EditionListResponse, EditionUpdate, EditionRead # pylint: disable=import-error

logger = logging.getLogger(__name__)


def get_editions(
    db: Session,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> EditionListResponse:
    """
    Búsqueda con paginación (limit/offset) y total.
    Incluye:
      - sales_count: SUM(Sale.total_portions)
      - edition_costs: SUM(EditionIngredient.subtotal)
      - net_profits: (sales_count * portion_price) - edition_costs
    """
    try:
        # construir filtros base
        filters = []
        if q:
            term = f"%{q.strip()}%"
            filters.append(or_(Edition.name.ilike(term), Edition.notes.ilike(term)))

        # total (sobre la consulta filtrada)
        base_count_stmt = select(Edition).where(*filters) if filters else select(Edition)
        count_stmt = select(func.count()).select_from(base_count_stmt.subquery())  # pylint: disable=not-callable
        total = db.execute(count_stmt).scalar_one()

        # subquery: sum of total_portions por edition
        sales_subq = (
            select(
                Sale.edition_id.label("edition_id"),
                func.coalesce(func.sum(Sale.total_portions), 0).label("sales_count"),
            )
            .group_by(Sale.edition_id)
            .subquery()
        )

        costs_subq = (
            select(
                EditionIngredient.edition_id.label("edition_id"),
                func.coalesce(func.sum(EditionIngredient.subtotal), 0).label("edition_costs"),
            )
            .group_by(EditionIngredient.edition_id)
            .subquery()
        )

        # select principal: Edition + sales_count + edition_costs (ambos opcionales por LEFT JOIN)
        rows_stmt = (
            select(Edition, sales_subq.c.sales_count, costs_subq.c.edition_costs)
            .outerjoin(sales_subq, sales_subq.c.edition_id == Edition.id)
            .outerjoin(costs_subq, costs_subq.c.edition_id == Edition.id)
        )

        # aplicar filtros si existen
        if filters:
            rows_stmt = rows_stmt.where(*filters)

        rows_stmt = rows_stmt.order_by(Edition.date.desc()).offset(offset).limit(limit)

        result = db.execute(rows_stmt).all()  # lista de tuples (Edition, sales_count, edition_costs)

        items = []
        for edition_obj, sales_count_raw, edition_costs_raw in result:
            edition_read = EditionRead.model_validate(edition_obj)

            # normalizar valores
            sales_count = int(sales_count_raw or 0)

            edition_costs_f = float(edition_costs_raw or 0.0)
            # como tu schema pide int, redondeo a entero (ajustalo si preferís float)
            edition_costs_int = int(round(edition_costs_f))

            # net_profits: si no hay portion_price devolvemos None (mantengo la misma lógica que sugeriste antes)
            if edition_obj.portion_price is None:
                net_profits_val = None
            else:
                revenue = float(sales_count) * float(edition_obj.portion_price)
                net_profit_f = revenue - edition_costs_f
                net_profits_val = int(round(net_profit_f))

            edition_read.sales_count = sales_count
            edition_read.edition_costs = edition_costs_int
            edition_read.net_profits = net_profits_val

            items.append(edition_read)

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
        logger.exception("Error al listar editions con búsqueda=%s", q)
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al listar ediciones"
        )


def get_edition(db: Session, edition_id: int):
    edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if edition is None:
        raise HTTPException(status_code=404, detail="Edition not found")

    try:
        # sales_count: SUM de total_portions para esta edition
        sales_count_stmt = select(func.coalesce(func.sum(Sale.total_portions), 0)).where(Sale.edition_id == edition_id)
        sales_count = db.execute(sales_count_stmt).scalar_one() or 0

        # edition_costs: SUM de subtotales de los edition_items para esta edition
        costs_stmt = select(func.coalesce(func.sum(EditionIngredient.subtotal), 0)).where(EditionIngredient.edition_id == edition_id)
        edition_costs_raw = db.execute(costs_stmt).scalar_one() or 0.0
        # normalizamos a float y redondeamos
        edition_costs = round(float(edition_costs_raw), 2)

        # net_profits: ingresos - costos
        if edition.portion_price is None:
            net_profits = None
        else:
            revenue = float(sales_count) * float(edition.portion_price)
            net_profits = round(revenue - edition_costs, 2)

        # construir response Pydantic
        edition_read = EditionRead.model_validate(edition)
        edition_read.sales_count = int(sales_count)
        edition_read.edition_costs = edition_costs
        edition_read.net_profits = net_profits

        return edition_read

    except SQLAlchemyError:
        logger.exception("Error al obtener edition %s", edition_id)
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al obtener edición"
        )


def create_edition(db: Session, edition: EditionCreate):
    db_edition = Edition(**edition.model_dump())
    db.add(db_edition)
    try:
        db.commit()
        db.refresh(db_edition)
        return EditionRead.model_validate(db_edition)
    except IntegrityError:
        db.rollback()
        logger.exception("Error de integridad al crear edición")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad en los datos de la edición"
        )


def update_edition(db: Session, edition_id: int, edition: EditionUpdate):
    db_edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if db_edition is None:
        raise HTTPException(status_code=404, detail="Edition not found")

    update_data = edition.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_edition, key, value)

    db.commit()
    db.refresh(db_edition)
    return EditionRead.model_validate(db_edition)


def delete_edition(db: Session, edition_id: int):
    db_edition = db.query(Edition).filter(Edition.id == edition_id).first()
    if db_edition is None:
        raise HTTPException(status_code=404, detail="Edition not found")

    db.delete(db_edition)
    db.commit()
    return EditionRead.model_validate(db_edition)
