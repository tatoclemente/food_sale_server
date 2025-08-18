from sqlalchemy.ext.declarative import as_declarative, declared_attr

@as_declarative()
class Base: # pylint: disable=too-few-public-methods
    @declared_attr  
    # pylint: disable=no-self-argument
    def __tablename__(cls) -> str:
        return cls.__name__.lower()