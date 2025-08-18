# models/purchase.py
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import (
    Column,
    BigInteger,
    String,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
from sqlalchemy import event

from db.base_class import Base  # pylint: disable=import-error

class PaymentStatus(PyEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"

class Purchase(Base):
    __tablename__ = "purchase"

    id = Column(BigInteger, primary_key=True, index=True)
    ingredient_id = Column(BigInteger, ForeignKey("ingredient.id", ondelete="CASCADE"), nullable=False, index=True)

    # link optional to edition for traceability
    edition_id = Column(BigInteger, ForeignKey("edition.id", ondelete="SET NULL"), nullable=True, index=True)

    purchased_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    supplier = Column(String(255), nullable=True)
    notes = Column(String, nullable=True)

    payment_status = Column(
        SQLEnum(PaymentStatus, name="payment_status", native_enum=False),
        nullable=False,
        default=PaymentStatus.PENDING,
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # relaciones
    ingredient = relationship("Ingredient", back_populates="purchases")
    edition = relationship("Edition", back_populates="purchases")
    # relación 1:1 (o 1:0..1) con edition_ingredient si querés navegar desde la compra
    edition_ingredient = relationship("EditionIngredient", back_populates="purchase", uselist=False)

    __table_args__ = (
        Index("ix_purchase_ingredient_paymentstatus", "ingredient_id", "payment_status"),
    )

@event.listens_for(Purchase, "before_insert")
def _purchase_before_insert(mapper, connection, target):
    if target.quantity is None or target.unit_price is None:
        return
    target.total_amount = round(target.quantity * target.unit_price, 2)

@event.listens_for(Purchase, "before_update")
def _purchase_before_update(mapper, connection, target):
    if target.quantity is None or target.unit_price is None:
        return
    target.total_amount = round(target.quantity * target.unit_price, 2)
