from typing import Generator
from db.session import SessionLocal # pylint: disable=import-error

def get_db() -> Generator:
    """
    Generator function to create a database session and yield it.
    This function is used to create a database session for each request and ensure proper resource cleanup.

    Yields:
        SessionLocal: A database session object.

    Example:
        >>> db = get_db()
        >>> # Use the database session
        >>> # When done, the session will be automatically closed
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()