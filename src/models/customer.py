from datetime import datetime, timezone
from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from db.base_class import Base # pylint: disable=import-error

class Customer(Base): # pylint: disable=too-few-public-methods
    __tablename__ = "customer"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    phone = Column(String, nullable=True, unique=True, index=True)
    email = Column(String, nullable=True, unique=True, index=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    editions = association_proxy('sales', 'edition') # view-only por defecto
    
    # Un cliente tiene muchas ventas
    sales = relationship(
        "Sale",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="select"
    )