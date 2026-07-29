from typing import TYPE_CHECKING, Any

from backend.app.models.base import Base
from sqlalchemy import BigInteger, CheckConstraint, Date, Integer, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    from datetime import datetime

class MilotoResult(Base):
    __tablename__ = "miloto_results"

    game_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    num_1: Mapped[int] = mapped_column(Integer, nullable=False)
    num_2: Mapped[int] = mapped_column(Integer, nullable=False)
    num_3: Mapped[int] = mapped_column(Integer, nullable=False)
    num_4: Mapped[int] = mapped_column(Integer, nullable=False)
    num_5: Mapped[int] = mapped_column(Integer, nullable=False)
    accumulated: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    hits_2: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)
    hits_3: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)
    hits_4: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)
    hits_5: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None, nullable=True)

    created_on: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    last_updated_on: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("game_id", "game_date", name="uq_miloto_results_game_id_date"),
        CheckConstraint(
            "num_1 >= 1 AND num_5 <= 39 AND num_1 < num_2 AND num_2 < num_3 AND num_3 < num_4 AND num_4 < num_5",
            name="ck_miloto_numbers_ascending",
        ),
    )
