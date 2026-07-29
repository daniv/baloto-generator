"""
Define shared validation models and behavior for lottery result schemas.

The module provides the common Pydantic base model used by Baloto, Revancha,
and MiLoto result schemas. It centralizes date parsing, combination identifier
generation, ascending-number validation, ORM serialization support, and the
structure used to represent prize details.
"""

import datetime
from abc import ABC, abstractmethod
from typing import Annotated

import dateparser
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, computed_field, field_validator

type AccumulatedField = Annotated[
    PositiveInt,
    Field(title="Acumulado", description="The accumulated prize value for the specific game; must be grater than 0"),
]


class BalotoMilotoBaseShema(BaseModel, ABC):
    """
    Provide shared validation and computed behavior for lottery result schemas.

    The schema defines fields common to Baloto, Revancha, and MiLoto results,
    including draw identification, draw date, ordered winning numbers, accumulated
    prize values, and payout details. It also centralizes date parsing, combination
    identifier generation, and validation shared by concrete result schemas.
    """

    model_config = ConfigDict(populate_by_name=True, frozen=True, from_attributes=True)

    game_id: Annotated[int, Field(ge=1, description="The game id", title="Sorteo")]
    game_date: Annotated[datetime.date, Field(..., description="Draw date", title="Fecha")]
    hits_3: ResultDetailsSchema | None = Field(
        default=None, description="3 hits prize distribution", title="Detalles de 3 aciertos"
    )
    hits_4: ResultDetailsSchema | None = Field(
        default=None, description="4-hit prize distribution", title="Detalles de 4 Aciertos"
    )
    hits_5: ResultDetailsSchema | None = Field(
        default=None, description="5-hit prize distribution", title="Detalles de 5 Aciertos"
    )
    accumulated: AccumulatedField = 0

    @computed_field
    @property
    def combination_id(self) -> str:
        """
        Return the stable identifier generated from the winning combination.

        :return: The encoded combination identifier produced by the concrete schema.
        """
        return self.calculate_combination_id()

    @field_validator("game_date", mode="before")
    @classmethod
    def parse_spanish_date(cls, value: object) -> datetime.date:
        """
        Parse a Spanish-language date into a ``datetime.date`` value.

        :param value: The raw date value supplied during schema validation.
        :return: The parsed calendar date.
        :raises TypeError: If the value is neither a string nor a ``datetime.date``.
        :raises ValueError: If the string cannot be parsed as a valid Spanish date.
        """
        if isinstance(value, datetime.date):
            return value
        if not isinstance(value, str):
            err_msg = "game_date must be a Spanish date string or datetime.date"
            raise TypeError(err_msg)

        parsed = dateparser.parse(value, languages=["es"], settings={"DATE_ORDER": "DMY", "STRICT_PARSING": True})

        if parsed is None:
            err_msg = f"Invalid Spanish date: {value!r}. Expected a value such as '7 de Julio de 2026'."
            raise ValueError(err_msg)

        return parsed.date()

    def _validate_ascending(self, numbers: list[int]) -> None:
        if numbers != sorted(numbers):
            err_msg = "Winning numbers must be in ascending order"
            raise ValueError(err_msg)
        if len(numbers) != len(set(numbers)):
            err_message = "All winning numbers must be unique"
            raise ValueError(err_message)

    @abstractmethod
    def calculate_combination_id(self) -> str:
        """
        Require concrete schemas to generate a stable combination identifier.

        Subclasses must implement this method using the encoding rules for their
        lottery product.

        :return: The encoded identifier produced by the concrete implementation.
        """


class ResultDetailsSchema(BaseModel):
    """
    Represent payout information for a specific lottery prize category.

    The schema stores the number of winners and the prize awarded to each winner.
    It is reused across Baloto, Revancha, and MiLoto result models to provide a
    consistent structure for prize-distribution data.
    """

    model_config = ConfigDict(populate_by_name=True, frozen=True, from_attributes=True)

    prize_for_winner: Annotated[int, Field(default=0, ge=0, description="Prize per winner", title="Premio por Ganador")]
    winners: Annotated[int, Field(default=0, ge=0, description="Number of winners", title="Ganadores")]
