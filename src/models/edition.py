from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, DateTime, Float
from sqlalchemy.orm import relationship
from db.base_class import Base # pylint: disable=import-error

class Edition(Base): # pylint: disable=too-few-public-methods
    __tablename__ = "edition"

    id = Column(BigInteger, primary_key=True, index=True)
    date = Column(DateTime, nullable=False)
    name = Column(String, nullable=False)
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