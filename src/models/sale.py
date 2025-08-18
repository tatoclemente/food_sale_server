from enum import Enum as PyEnum
from datetime import datetime, timezone
import sqlalchemy as sa
from sqlalchemy import Column, Float, Index, DateTime, BigInteger, String, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum as SAEnum
from db.base_class import Base # pylint: disable=import-error

class PaymentStatus(PyEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"
    
class Sale(Base): # pylint: disable=too-few-public-methods
    __tablename__ = "sale"
    
    __table_args__ = (
        Index('ix_sale_customer_edition', 'customer_id', 'edition_id'),  # índice compuesto
    )

    id = Column(BigInteger, primary_key=True, index=True)
    total_amount = Column(Float, nullable=True)
    total_portions = Column(Integer, nullable=False)
    # Usamos SAEnum con native_enum=True para crear un enum nativo en Postgres
    payment_status = Column(
        SAEnum(PaymentStatus, name="paymentstatus", native_enum=True),
        nullable=False,
        server_default=sa.text("'PENDING'")
    )
    payment_transfer = Column(Boolean, default=False)
    delivered = Column(Boolean, default=False)
    saved = Column(Boolean, default=False)
    additional_cost = Column(Float, nullable=True)
    sold_by = Column(BigInteger, nullable=True)
    seller_name = Column(String, nullable=True)
    discount_price = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    customer_id = Column(BigInteger, ForeignKey("customer.id"), nullable=False, index=True)
    edition_id = Column(BigInteger, ForeignKey("edition.id"), nullable=False, index=True)

    # Relaciones (singular en el lado 'many-to-one' para claridad)
    customer = relationship("Customer", back_populates="sales")
    edition = relationship("Edition", back_populates="sales")