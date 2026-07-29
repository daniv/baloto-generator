"""
Model registry for the application.

Importing this package ensures every ORM model class below is registered
on :attr:`Base.metadata`. This is required for
:meth:`Base.metadata.create_all` (used in tests) and for Alembic's
autogenerate to detect all tables.

Add a new import line here every time a new model module is created.
"""

from app.models.baloto_db import BalotoResult
from app.models.base import Base
from app.models.miloto_db import MilotoResult
from app.models.revancha_db import RevanchaResult

__all__ = [
    "BalotoResult",
    "Base",
    "MilotoResult",
    "RevanchaResult",
]
