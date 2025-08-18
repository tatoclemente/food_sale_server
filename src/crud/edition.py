import logging
from typing import Any, Dict, Optional
from sqlalchemy import or_, func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from fastapi import HTTPException, status

from models.edition import Edition
from schemas.edition import EditionCreate, EditionUpdate, EditionRead

logger = logging.getLogger(__name__)


def get_editions(
    db: Session,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Búsqueda con paginación (limit/offset) y total.
    Retorna dict con keys: items, total, limit, offset, next_offset, prev_offset
    """
    try:
        stmt = select(Edition)
        if q:
            term = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Edition.name.ilike(term),
                    Edition.notes.ilike(term)
                )
            )

        # total
        count_stmt = select(func.count()).select_from(stmt.subquery()) # pylint: disable=not-callable
        total = db.execute(count_stmt).scalar_one()

        # filas
        rows_stmt = stmt.order_by(Edition.date.desc()).offset(offset).limit(limit)
        rows = db.execute(rows_stmt).scalars().all()

        items = [EditionRead.model_validate(r) for r in rows]

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
    return EditionRead.model_validate(edition)


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
