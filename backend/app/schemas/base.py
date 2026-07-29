import datetime
from abc import ABC, abstractmethod
from typing import Annotated, Any

import dateparser
from pydantic import BaseModel, ConfigDict, Field, PositiveInt, computed_field, field_validator

type AccumulatedField = Annotated[
    PositiveInt,
    Field(title="Acumulado", description="The accumulated prize value for the specific game; must be grater than 0"),
]


class BalotoMilotoBaseShema(BaseModel, ABC):
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
        return self.calculate_combination_id()

    @field_validator("game_date", mode="before")
    @classmethod
    def parse_spanish_date(cls, value: Any) -> datetime.date:
        if isinstance(value, datetime.date):
            return value
        if not isinstance(value, str):
            raise TypeError("game_date must be a Spanish date string or datetime.date")

        parsed = dateparser.parse(value, languages=["es"], settings={"DATE_ORDER": "DMY", "STRICT_PARSING": True})

        if parsed is None:
            raise ValueError(f"Invalid Spanish date: {value!r}. Expected a value such as '7 de Julio de 2026'.")

        return parsed.date()

    def _validate_ascending(self, numbers: list[int]) -> None:
        if numbers != sorted(numbers):
            raise ValueError("Winning numbers must be in ascending order")
        if len(numbers) != len(set(numbers)):
            raise ValueError("All winning numbers must be unique")

    @abstractmethod
    def calculate_combination_id(self) -> str:
        pass


class ResultDetailsSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True, frozen=True, from_attributes=True)

    prize_for_winner: Annotated[int, Field(default=0, ge=0, description="Prize per winner", title="Premio por Ganador")]
    winners: Annotated[int, Field(default=0, ge=0, description="Number of winners", title="Ganadores")]
