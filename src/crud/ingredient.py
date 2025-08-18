import logging
from typing import Optional
from sqlalchemy import String, cast, or_, func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from fastapi import HTTPException, status

from models.ingredient import Ingredient # pylint: disable=import-error
from schemas.ingredient import ( # pylint: disable=import-error
    IngredientCreate, 
    IngredientListResponse, 
    IngredientRead,
    IngredientUpdate
)

logger = logging.getLogger(__name__)

def get_ingredients(
    db: Session,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> IngredientListResponse:
    """
    Búsqueda con paginación (limit/offset) y total.
    Retorna dict con keys: items, total, limit, offset, next_offset, prev_offset
    """
    try:
        stmt = select(Ingredient)
        if q:
            term = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Ingredient.name.ilike(term),
                    Ingredient.unit.ilike(term),
                    cast(Ingredient.category, String).ilike(term)  # depende si el Enum se guarda como string
                )
            )

        # total
        count_stmt = select(func.count()).select_from(stmt.subquery()) # pylint: disable=not-callable
        total = db.execute(count_stmt).scalar_one()

        # filas
        rows_stmt = stmt.order_by(Ingredient.created_at.desc()).offset(offset).limit(limit)
        rows = db.execute(rows_stmt).scalars().all()

        items = [IngredientRead.model_validate(r) for r in rows]

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
        logger.exception("Error al listar ingredients con búsqueda=%s", q)
        raise HTTPException(
            status_code=500,
            detail="Error de base de datos al listar ingredientes"
        )


def get_ingredient(db: Session, ingredient_id: int):
    ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")
    return IngredientRead.model_validate(ingredient)


def create_ingredient(db: Session, ingredient: IngredientCreate):
    db_ingredient = Ingredient(**ingredient.model_dump())
    db.add(db_ingredient)
    try:
        db.commit()
        db.refresh(db_ingredient)
        return IngredientRead.model_validate(db_ingredient)
    except IntegrityError:
        db.rollback()
        logger.exception("Error de integridad al crear ingredient")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad en los datos del ingrediente"
        )


def update_ingredient(db: Session, ingredient_id: int, ingredient: IngredientUpdate):
    db_ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if db_ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    update_data = ingredient.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_ingredient, key, value)

    db.commit()
    db.refresh(db_ingredient)
    return IngredientRead.model_validate(db_ingredient)


def delete_ingredient(db: Session, ingredient_id: int):
    db_ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()
    if db_ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    db.delete(db_ingredient)
    db.commit()
    return IngredientRead.model_validate(db_ingredient)
