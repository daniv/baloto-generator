"""
Define the Baloto result persistence model.

The module maps Baloto draw data to the ``baloto_results`` table, including
winning numbers, the Super Balota value, accumulated prizes, payout details,
timestamps, uniqueness constraints, and database-level validation rules.
"""

from datetime import datetime  # noqa: TC003 -- SQLAlchemy resolves Mapped annotations at runtime.
from typing import Any

from sqlalchemy import BigInteger, CheckConstraint, Date, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BalotoResult(Base):
    """
    Map a Baloto draw result to the ``baloto_results`` database table.

    The model stores the draw identifier and date, ordered winning numbers,
    Super Balota value, accumulated jackpot, prize distributions, and audit
    timestamps. Table constraints enforce valid number ranges, ascending order,
    and uniqueness for each draw.
    """

    __tablename__ = "baloto_results"

    game_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    num_1: Mapped[int] = mapped_column(Integer, nullable=False)
    num_2: Mapped[int] = mapped_column(Integer, nullable=False)
    num_3: Mapped[int] = mapped_column(Integer, nullable=False)
    num_4: Mapped[int] = mapped_column(Integer, nullable=False)
    num_5: Mapped[int] = mapped_column(Integer, nullable=False)
    balota: Mapped[int] = mapped_column(Integer, nullable=False)
    accumulated: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    hits_3: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)
    hits_4: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)
    hits_5: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)
    hits_sb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)
    hits_2_sb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)
    hits_3_sb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)
    hits_4_sb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)
    hits_5_sb: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)

    created_on: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_updated_on: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("game_id", "game_date", name="uq_baloto_results_game_id_date"),
        CheckConstraint(
            "num_1 >= 1 AND num_5 <= 43 AND num_1 < num_2 AND num_2 < num_3 AND num_3 < num_4 AND num_4 < num_5",
            name="ck_baloto_numbers_ascending",
        ),
        CheckConstraint("balota BETWEEN 1 AND 16", name="ck_baloto_balota"),
    )
