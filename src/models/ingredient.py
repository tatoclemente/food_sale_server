from enum import Enum as PyEnum
from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, DateTime, Float
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum as SAEnum
from db.base_class import Base  # pylint: disable=import-error

class Category(PyEnum):
    MEAT = "MEAT"
    SAUSAGES = "SAUSAGES"
    LEGUMES = "LEGUMES"
    VEGETABLES = "VEGETABLES"
    STORE = "STORE"
    DISPOSABLE = "DISPOSABLE"
    OTHER = "OTHER"

class Ingredient(Base):
    __tablename__ = "ingredient"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    unit_price = Column(Float, nullable=False, default=0.0)
    unit = Column(String(32), nullable=False, default="kg")
    category = Column(SAEnum(Category, name="category", native_enum=True), nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc),
                        onupdate=datetime.now(timezone.utc))

    purchases = relationship(
        "Purchase",
        back_populates="ingredient",
        cascade="all, delete-orphan",
        lazy="select"
    )
    edition_items = relationship(
        "EditionIngredient", 
        back_populates="ingredient", 
        cascade="all, delete-orphan", 
        lazy="select"
    )