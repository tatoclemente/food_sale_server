import sqlalchemy as sa
from sqlalchemy.types import Enum as SAEnum
from sqlalchemy import Column, BigInteger, String, DateTime, Float
from sqlalchemy.orm import relationship
from enum import Enum as PyEnum
from datetime import datetime, timezone
from db.base_class import Base # pylint: disable=import-error

class EditionStatus(PyEnum):
    PENDING= "PENDING"
    ACTIVE = "ACTIVE"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"
class Edition(Base): # pylint: disable=too-few-public-methods
    __tablename__ = "edition"

    id = Column(BigInteger, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    name = Column(String, nullable=False)
    status = Column(
        SAEnum(EditionStatus, name="editionstatus", native_enum=True),
        nullable=False,
        server_default=sa.text("'PENDING'")
    )
    portion_price = Column(Float, nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    # Una edición tiene muchas ventas
    sales = relationship(
        "Sale",
        back_populates="edition",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    edition_items = relationship(
        "EditionIngredient",
        back_populates="edition",
        cascade="all, delete-orphan",
        lazy="select"
    )
    
    purchases = relationship(
        "Purchase",
        back_populates="edition",
        cascade="all, delete-orphan",
        lazy="select"
    )