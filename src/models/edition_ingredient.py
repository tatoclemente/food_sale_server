from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, Float, DateTime, ForeignKey, UniqueConstraint, String
from sqlalchemy.orm import relationship
from db.base_class import Base  # pylint: disable=import-error

class EditionIngredient(Base):
    __tablename__ = "edition_ingredient"
    __table_args__ = (
        UniqueConstraint('edition_id', 'ingredient_id', name='uq_edition_ingredient'),
    )

    id = Column(BigInteger, primary_key=True, index=True)
    edition_id = Column(BigInteger, ForeignKey("edition.id", ondelete="CASCADE"), nullable=False, index=True)
    ingredient_id = Column(BigInteger, ForeignKey("ingredient.id", ondelete="CASCADE"), nullable=False, index=True)

    # nuevo: referencia a la compra asociada si fue creada junto con este item
    purchase_id = Column(BigInteger, ForeignKey("purchase.id", ondelete="SET NULL"), nullable=True, index=True)

    quantity = Column(Float, nullable=False, default=0.0)
    unit_price = Column(Float, nullable=False, default=0.0)
    subtotal = Column(Float, nullable=False, default=0.0)

    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    edition = relationship("Edition", back_populates="edition_items")
    ingredient = relationship("Ingredient", back_populates="edition_items")

    # relación con Purchase
    purchase = relationship("Purchase", back_populates="edition_ingredient", lazy="joined")

    def compute_subtotal(self) -> float:
        q = float(self.quantity or 0.0)
        p = float(self.unit_price or 0.0)
        self.subtotal = round(q * p, 2)
        return self.subtotal
