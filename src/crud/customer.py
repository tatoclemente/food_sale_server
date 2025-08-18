import logging
from typing import Optional
from sqlalchemy import or_, func, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from models.customer import Customer # pylint: disable=import-error
from schemas.customer import CustomerCreate, CustomerListResponse, CustomerUpdate, CustomerRead # pylint: disable=import-error
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

def get_customers(
    db: Session,
    q: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> CustomerListResponse:
    """
    Búsqueda con paginación (limit/offset) y total.
    Retorna dict con keys: items, total, limit, offset, next_offset, prev_offset
    """
    try:
        # 1) construir la sentencia base (select) con filtros si aplica
        stmt = select(Customer)
        if q:
            term = f"%{q.strip()}%"
            stmt = stmt.where(
                or_(
                    Customer.name.ilike(term),
                    Customer.email.ilike(term),
                    Customer.phone.ilike(term),
                )
            )

        # 2) calcular total usando select(func.count()) sobre la subquery del stmt
        #    esto es eficiente y evita problemas de composición directos con Query.count()
        count_stmt = select(func.count()).select_from(stmt.subquery()) # pylint: disable=not-callable
        total = db.execute(count_stmt).scalar_one()  # devuelve un int

        # 3) traer las filas aplicando orden/offset/limit
        rows_stmt = stmt.order_by(Customer.name).offset(offset).limit(limit)
        rows = db.execute(rows_stmt).scalars().all()

        items = [CustomerRead.model_validate(r) for r in rows]

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
        logger.exception("Error al listar customers con búsqueda=%s", q)
        raise HTTPException(status_code=500, detail="Error de base de datos al listar clientes")

def get_customer(db: Session, customer_id: int):
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerRead(**customer.__dict__)
    

def create_customer(db: Session, customer: CustomerCreate):
    db_customer = Customer(**customer.model_dump())
    db.add(db_customer)
    try:
        db.commit()
        db.refresh(db_customer)
        return db_customer
    except IntegrityError as exc:
        db.rollback()
        if "email" in str(exc.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email ya está registrado"
            )
        if "phone" in str(exc.orig):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El teléfono ya está registrado"
            )
      
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error de integridad en los datos"
        )

def update_customer(db: Session, customer_id: int, customer: CustomerUpdate):
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if db_customer:
        update_data = customer.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_customer, key, value)
        db.commit()
        db.refresh(db_customer)
    return db_customer

def delete_customer(db: Session, customer_id: int):
    db_customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if db_customer:
        db.delete(db_customer)
        db.commit()
    return db_customer