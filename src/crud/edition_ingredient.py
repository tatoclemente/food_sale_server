# crud/edition_ingredient.py (adaptado)
import logging
from enum import Enum as PyEnum
from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from fastapi import HTTPException, status

from models.edition_ingredient import EditionIngredient  # pylint: disable=import-error
from models.edition import Edition  # pylint: disable=import-error
from models.ingredient import Category, Ingredient  # pylint: disable=import-error
from models.purchase import Purchase # pylint: disable=import-error
from schemas.edition_ingredient import (  # pylint: disable=import-error
    EditionIngredientCreate,
    EditionIngredientRead,
    EditionIngredientListResponse,
    EditionIngredientUpdate,
)

logger = logging.getLogger(__name__)

def _round2(v: float) -> float:
    return round(float(v or 0.0), 2)

def _compute_subtotal(quantity: float, unit_price: float) -> float:
    return _round2(quantity * unit_price)

def _make_read_from_instance(instance: EditionIngredient) -> EditionIngredientRead:
    """
    Intenta validar desde el objeto; si falta subtotal, lo calcula.
    """
    try:
        read = EditionIngredientRead.model_validate(instance)
        # si subtotal no viene del modelo, lo calculamos
        if getattr(read, "subtotal", None) in (None,):
            qty = getattr(instance, "quantity", None)
            price = getattr(instance, "unit_price", None)
            if qty is not None and price is not None:
                computed = float(qty) * float(price)
                payload = {
                    "id": getattr(instance, "id", None),
                    "ingredient_id": getattr(instance, "ingredient_id", None),
                    "quantity": getattr(instance, "quantity", None),
                    "unit_price": getattr(instance, "unit_price", None),
                    "notes": getattr(instance, "notes", None),
                    "subtotal": computed,
                    "created_at": getattr(instance, "created_at", None),
                    # incluir relaciones si existen
                    "ingredient": getattr(instance, "ingredient", None),
                    "edition": getattr(instance, "edition", None),
                    "purchase": getattr(instance, "purchase", None),
                }
                return EditionIngredientRead.model_validate(payload)
        return read
    except Exception:
        # fallback manual
        qty = getattr(instance, "quantity", None)
        price = getattr(instance, "unit_price", None)
        computed = (float(qty) * float(price)) if (qty is not None and price is not None) else None
        payload = {
            "id": getattr(instance, "id", None),
            "ingredient_id": getattr(instance, "ingredient_id", None),
            "quantity": qty,
            "unit_price": price,
            "notes": getattr(instance, "notes", None),
            "subtotal": computed,
            "created_at": getattr(instance, "created_at", None),
            "ingredient": getattr(instance, "ingredient", None),
            "edition": getattr(instance, "edition", None),
            "purchase": getattr(instance, "purchase", None),
        }
        return EditionIngredientRead.model_validate(payload)


def _parse_categories_param(categories_param: Optional[str]) -> Optional[List[Category]]:
    """
    Convierte 'MEAT,VEGETABLES' -> [Category.MEAT, Category.VEGETABLES]
    Devuelve None si categories_param es None o vacío.
    Lanza HTTPException(400) si hay un valor inválido.
    """
    if not categories_param:
        return None

    raw_items = [c.strip() for c in categories_param.split(",") if c.strip()]
    if not raw_items:
        return None

    parsed: List[Category] = []
    errors = []
    for item in raw_items:
        try:
            # aceptar tanto 'MEAT' como 'MEAT' exacto; si usás .value diferente, Category(item) también funciona
            parsed.append(Category(item))
        except Exception:
            # intentar por name (por si alguien pasa 'MEAT' y la Enum fue definida con otro)
            try:
                parsed.append(Category[item])
            except Exception:
                errors.append(item)

    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid category values: {', '.join(errors)}"
        )
    return parsed


def get_edition_ingredients(
    db: Session,
    edition_id: Optional[int] = None,
    q: Optional[str] = None,
    categories: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> EditionIngredientListResponse:
    """
    Lista los ingredientes de ediciones (opcional: filtrar por edition_id).
    Busca por notes si q está presente.
    Además retorna totales por categoría y el total de gastos (purchases).
    """
    try:
        
        parsed_categories = _parse_categories_param(categories)
        
        base_q = db.query(EditionIngredient).options(
            joinedload(EditionIngredient.ingredient),
            joinedload(EditionIngredient.edition),
            joinedload(EditionIngredient.purchase),
        )

        # aplicar filtros
        if edition_id is not None:
            base_q = base_q.filter(EditionIngredient.edition_id == edition_id)

        if q:
            term = f"%{q.strip()}%"
            base_q = base_q.filter(EditionIngredient.notes.ilike(term))
        
        if parsed_categories is not None:
            # SQLAlchemy puede comparar Enum column con Python Enum instances
            base_q = base_q.join(Ingredient, Ingredient.id == EditionIngredient.ingredient_id).filter(
                Ingredient.category.in_(parsed_categories)
            )

        # total count (paginación)
        total = base_q.count()

        # filas paginadas
        rows = base_q.order_by(EditionIngredient.created_at.desc()).offset(offset).limit(limit).all()

        items = [_make_read_from_instance(r) for r in rows]

        # ---------------------------
        # Totales por categoría
        # ---------------------------
        # join Ingredient para agrupar por category
        cat_q = db.query(
            Ingredient.category.label("category"),
            func.coalesce(func.sum(EditionIngredient.subtotal), 0.0).label("total")
        ).join(
            Ingredient,
            Ingredient.id == EditionIngredient.ingredient_id
        )

        # aplicar mismos filtros que en base_q
        if edition_id is not None:
            cat_q = cat_q.filter(EditionIngredient.edition_id == edition_id)
        if q:
            cat_q = cat_q.filter(EditionIngredient.notes.ilike(term))

        cat_q = cat_q.group_by(Ingredient.category)
        cat_rows = cat_q.all()

        # normalizar a lista de dicts
        category_totals = []
        for cat, tot in cat_rows:
            # si cat es un Enum, tomar .value o .name; si no, fallback a str(cat)
            if isinstance(cat, PyEnum):
                label = cat.value  # o cat.name si preferís el nombre del enum
            else:
                label = str(cat)
            category_totals.append({"category": label, "total": float(tot or 0.0)})
        # ---------------------------
        # Total de subtotales (ingredientes)
        # ---------------------------
        total_sub_q = db.query(func.coalesce(func.sum(EditionIngredient.subtotal), 0.0))
        if edition_id is not None:
            total_sub_q = total_sub_q.filter(EditionIngredient.edition_id == edition_id)
        if q:
            total_sub_q = total_sub_q.filter(EditionIngredient.notes.ilike(term))
        ingredients_total = float(total_sub_q.scalar() or 0.0)

        # ---------------------------
        # Total de gastos (purchases)
        # ---------------------------
        # Si pasaron edition_id, sumamos purchases para esa edición.
        # Si no, devolvemos la suma total de purchases (podés cambiar esto si preferís None en ese caso).
        expenses_q = db.query(func.coalesce(func.sum(Purchase.total_amount), 0.0))
        if edition_id is not None:
            expenses_q = expenses_q.filter(Purchase.edition_id == edition_id)
        total_expenses = float(expenses_q.scalar() or 0.0)

        # ---------------------------
        # construir respuesta
        # ---------------------------
        next_offset = offset + limit if (offset + limit) < total else None
        prev_offset = offset - limit if (offset - limit) >= 0 else None

        return EditionIngredientListResponse(
            items=items,
            total=int(total),
            limit=limit,
            offset=offset,
            next_offset=next_offset,
            prev_offset=prev_offset,
            category_totals=category_totals,
            ingredients_total=ingredients_total,
            total_expenses=total_expenses
        )

    except SQLAlchemyError:
        logger.exception("Error al listar edition_ingredients edition_id=%s q=%s", edition_id, q)
        raise HTTPException(status_code=500, detail="Error de base de datos al listar edition_ingredients")


def get_edition_ingredient(db: Session, ei_id: int) -> EditionIngredientRead:
    ei = (
        db.query(EditionIngredient)
        .options(
            joinedload(EditionIngredient.ingredient),
            joinedload(EditionIngredient.edition),
            joinedload(EditionIngredient.purchase),
        )
        .filter(EditionIngredient.id == ei_id)
        .first()
    )
    if ei is None:
        raise HTTPException(status_code=404, detail="EditionIngredient not found")
    return _make_read_from_instance(ei)



def create_edition_ingredient(
    db: Session,
    edition_id: int,
    payload: EditionIngredientCreate,
    *,
    strategy: str = "sum",         # "sum" | "replace" | "nothing"
    autonomous: bool = True        # si True abre SU propia sesión y commitea
) -> EditionIngredientRead:
    """
    Crea purchase + edition_ingredient con control de transacción flexible.

    - Si autonomous=True: abre su propia Session/transaction (commit garantizado aquí).
      Útil para endpoints HTTP donde querés que la operación quede persistida aunque
      la Session del caller tenga transacciones abiertas.
    - Si autonomous=False: intenta usar la Session `db` provista. Si ya hay transacción,
      usa SAVEPOINT (db.begin_nested()). En este modo NO hace commit final (lo hace el caller).
    """
    # 1) Validaciones rápidas (fuera de la transacción)
    edition = db.get(Edition, edition_id)
    if edition is None:
        raise HTTPException(status_code=404, detail="Edition not found")
    ingredient = db.get(Ingredient, payload.ingredient_id)
    if ingredient is None:
        raise HTTPException(status_code=404, detail="Ingredient not found")

    qty_new = float(payload.quantity or 0.0)
    unit_price_new = (
        float(payload.unit_price)
        if getattr(payload, "unit_price", None) is not None
        else float(ingredient.unit_price or 0.0)
    )
    notes = getattr(payload, "notes", None)

    def _do_work(session: Session) -> EditionIngredientRead:
        """
        Ejecuta la lógica de DB usando la Session `session` (que ya está en un contexto transaction).
        """
        # bloquear fila existente para concurrencia
        existing: Optional[EditionIngredient] = (
            session.query(EditionIngredient)
            .filter(
                EditionIngredient.edition_id == edition_id,
                EditionIngredient.ingredient_id == payload.ingredient_id,
            )
            .with_for_update(of=EditionIngredient, read=False)
            .first()
        )

        def _create_purchase(qty: float, unit_price: float) -> Purchase:
            p = Purchase(
                ingredient_id=payload.ingredient_id,
                edition_id=edition_id,
                purchased_at=datetime.now(timezone.utc),
                quantity=qty,
                unit_price=unit_price,
                payment_status="PENDING",
                total_amount=_compute_subtotal(qty, unit_price),
                supplier=None,
                notes=None,
            )
            session.add(p)
            session.flush()  # obtiene p.id
            return p

        # No existe -> crear purchase + edition_ingredient
        if existing is None:
            purchase = _create_purchase(qty_new, unit_price_new)
            ei = EditionIngredient(
                edition_id=edition_id,
                ingredient_id=payload.ingredient_id,
                quantity=qty_new,
                unit_price=unit_price_new,
                subtotal=_compute_subtotal(qty_new, unit_price_new),
                notes=notes,
                purchase_id=purchase.id,
            )
            session.add(ei)
            session.flush()
            ei = (
                session.query(EditionIngredient)
                .options(
                    joinedload(EditionIngredient.ingredient),
                    joinedload(EditionIngredient.edition),
                    joinedload(EditionIngredient.purchase),
                )
                .get(ei.id)
            )
            return EditionIngredientRead.model_validate(ei)

        # Existe y estrategia nothing
        if strategy == "nothing":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ingredient already added to this edition")

        # strategy replace
        if strategy == "replace":
            purchase = _create_purchase(qty_new, unit_price_new)
            existing.quantity = qty_new
            existing.unit_price = unit_price_new
            existing.subtotal = _compute_subtotal(qty_new, unit_price_new)
            existing.notes = notes
            existing.purchase_id = purchase.id
            existing.updated_at = datetime.now(timezone.utc)
            session.add(existing)
            session.flush()
            existing = (
                session.query(EditionIngredient)
                .options(
                    joinedload(EditionIngredient.ingredient),
                    joinedload(EditionIngredient.edition),
                    joinedload(EditionIngredient.purchase),
                )
                .get(existing.id)
            )
            return EditionIngredientRead.model_validate(existing)

        # strategy sum (acumular)
        purchase = _create_purchase(qty_new, unit_price_new)
        prev_qty = float(existing.quantity or 0.0)
        prev_sub = float(existing.subtotal or 0.0)
        add_sub = _compute_subtotal(qty_new, unit_price_new)

        existing.quantity = prev_qty + qty_new
        if getattr(payload, "unit_price", None) is not None:
            existing.unit_price = unit_price_new
        existing.subtotal = _round2(prev_sub + add_sub)
        existing.notes = notes or existing.notes
        existing.purchase_id = purchase.id
        existing.updated_at = datetime.now(timezone.utc)
        session.add(existing)
        session.flush()

        existing = (
            session.query(EditionIngredient)
            .options(
                joinedload(EditionIngredient.ingredient),
                joinedload(EditionIngredient.edition),
                joinedload(EditionIngredient.purchase),
            )
            .get(existing.id)
        )
        return EditionIngredientRead.model_validate(existing)

    # -------------------------------------
    # flujo de transacciones según autonomous y estado del `db`
    # -------------------------------------
    # Si el caller pidió que la función sea autónoma, abrimos NUESTRA sesión/transaction
    if autonomous:
        # crear una nueva Session ligada al mismo engine/connection
        bind = db.get_bind()
        # SessionType es sqlalchemy.orm.Session
        new_sess = Session(bind=bind)
        try:
            with new_sess.begin():
                result = _do_work(new_sess)
                # commit se realiza al salir del with
                return result
        except IntegrityError as e:
            new_sess.rollback()
            pgcode = getattr(getattr(e, "orig", None), "pgcode", None)
            logger.exception("IntegrityError (autonomous): %s", e)
            if pgcode == "23505":
                raise HTTPException(status_code=409, detail="Conflict (unique violation)")
            raise HTTPException(status_code=400, detail="Integrity error")
        except SQLAlchemyError as e:
            new_sess.rollback()
            logger.exception("DB error (autonomous): %s", e)
            raise HTTPException(status_code=500, detail="Database error")
        finally:
            new_sess.close()

    # Si no es autónoma: operar sobre la Session `db` provista
    # Si ya hay una transacción abierta, usar SAVEPOINT (begin_nested)
    try:
        if db.in_transaction():
            # usar savepoint; el caller debe hacer commit del outer transaction
            with db.begin_nested():
                return _do_work(db)
        else:
            # abrir una transacción normal en la session provista
            with db.begin():
                return _do_work(db)
    except IntegrityError as e:
        # mapear errores
        pgcode = getattr(getattr(e, "orig", None), "pgcode", None)
        logger.exception("IntegrityError (non-autonomous): %s", e)
        if pgcode == "23505":
            raise HTTPException(status_code=409, detail="Conflict (unique violation)")
        raise HTTPException(status_code=400, detail="Integrity error")
    except SQLAlchemyError as e:
        logger.exception("DB error (non-autonomous): %s", e)
        raise HTTPException(status_code=500, detail="Database error")


def update_edition_ingredient(db: Session, id: int, payload: EditionIngredientUpdate):
    db_ei = db.query(EditionIngredient).filter(EditionIngredient.id == id).first()
    if not db_ei:
        raise HTTPException(status_code=404, detail="Not found")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(db_ei, k, v)

    # si cambiaron quantity o unit_price, recomputar
    if "quantity" in data or "unit_price" in data:
        db_ei.compute_subtotal()

    db.commit()
    db.refresh(db_ei)
    return _make_read_from_instance(db_ei)


def delete_edition_ingredient(db: Session, ei_id: int):
    db_ei = db.query(EditionIngredient).filter(EditionIngredient.id == ei_id).first()
    if db_ei is None:
        raise HTTPException(status_code=404, detail="EditionIngredient not found")

    result = _make_read_from_instance(db_ei)
    db.delete(db_ei)
    db.commit()
    return result
