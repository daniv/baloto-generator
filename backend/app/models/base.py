"""
Define the shared declarative base for SQLAlchemy persistence models.

The module exposes the common ``Base`` class inherited by all database models.
It provides the SQLAlchemy registry and metadata used to map application
entities, create tables during tests, and coordinate schema-level operations.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Provide the shared declarative base for all SQLAlchemy models.

    Subclasses inherit the registry and metadata used to map application entities,
    create database tables during tests, and coordinate schema-level operations
    across the persistence layer.
    """
