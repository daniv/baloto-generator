from abc import ABC, abstractmethod
from typing import Annotated, Self

from backend.app.config.app_settings import settings
from backend.app.schemas.base import AccumulatedField, BalotoMilotoBaseShema, ResultDetailsSchema
from backend.app.utils.math_utils import numbers_to_hex
from pydantic import (
    Field,
    PrivateAttr,
    model_validator,
)


class _SharedBalotoRevanchaResultSchema(BalotoMilotoBaseShema, ABC):
    """
    Fields shared by Baloto and Revancha results, with no write-time validators.

    Used directly for reading stored results (API responses), where
    validators tied to current settings — such as the minimum jackpot —
    must not reject a historical row just because a rule changed after
    that row was written.
    """

    num_1: Annotated[int, Field(ge=1, le=39, description="First winning number", title="1er Numero Ganador")]
    num_2: Annotated[int, Field(ge=2, le=40, description="Second winning number", title="2do Numero Ganador")]
    num_3: Annotated[int, Field(ge=3, le=41, description="Third winning number", title="3er Numero Ganador")]
    num_4: Annotated[int, Field(ge=4, le=42, description="Fourth winning number", title="4to Numero Ganador")]
    num_5: Annotated[int, Field(ge=5, le=43, description="Fifth winning number", title="5to Numero Ganador")]
    balota: Annotated[int, Field(ge=1, le=16, description="Super Balota number", title="Super Balota")]
    accumulated: AccumulatedField = settings.baloto_settings.baloto_min_jackpot
    hits_sb: ResultDetailsSchema | None = Field(
        default=None,
        description="Only super balota prize distribution",
        title="Detalles de acierto solo en Super Balota 1+SB o 0+SB",
    )
    hits_2_sb: ResultDetailsSchema | None = Field(
        default=None,
        description="2 hits + super balota prize distribution",
        title="Detalles de 2 aciertos mas Super Balota 2+SB",
    )
    hits_3_sb: ResultDetailsSchema | None = Field(
        default=None,
        description="3 hits + super balota prize distribution",
        title="Detalles de 3 aciertos mas Super Balota: 3+SB",
    )
    hits_4_sb: ResultDetailsSchema | None = Field(
        default=None,
        description="4 hits + super balota prize distribution",
        title="Detalles de 4 aciertos mas Super Balota: 4+SB",
    )
    hits_5_sb: ResultDetailsSchema | None = Field(
        default=None,
        description="5 hits + super balota prize distribution",
        title="Detalles de 5 aciertos mas Super Balota: 5+SB (jackpot)",
    )

    @property
    @abstractmethod
    def type(self) -> str:
        """Abstract property that every subclass must implement."""

    @model_validator(mode="after")
    def check_ascending(self) -> Self:
        """Validate that num_1 through num_5 are ordered."""
        numbers = [self.num_1, self.num_2, self.num_3, self.num_4, self.num_5]
        self._validate_ascending(numbers)
        return self

    def calculate_combination_id(self) -> str:
        """Claculates the hexa represenation of the winning combination"""
        combination_hex = numbers_to_hex(
            (self.num_1, self.num_2, self.num_3, self.num_4, self.num_5), settings.baloto_settings.baloto_max_num
        )
        balota_hex = f"{self.balota:X}"
        return f"{combination_hex}:{balota_hex}"


class BalotoResultSchema(_SharedBalotoRevanchaResultSchema):
    _type: str = PrivateAttr(default="B")

    @property
    def type(self) -> str:
        # Exposes the private attribute publicly for reading
        return self._type


class RevanchaResultSchema(_SharedBalotoRevanchaResultSchema):
    _type: str = PrivateAttr(default="R")

    @property
    def type(self) -> str:
        # Exposes the private attribute publicly for reading
        return self._type
