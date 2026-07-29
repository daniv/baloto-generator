from typing import Annotated, Self

from pydantic import ConfigDict, Field, computed_field, field_validator, model_validator

from backend.app.schemas.base import AccumulatedField, BalotoMilotoBaseShema, ResultDetailsSchema
from backend.app.config.app_settings import settings
from backend.app.utils.math_utils import numbers_to_hex
from backend.app.utils.date_utils import full_date


class MilotoResultSchema(BalotoMilotoBaseShema):
    model_config = ConfigDict(populate_by_name=True, frozen=True, from_attributes=True)
    
    num_1: Annotated[int, Field(ge=1, le=35, description="First winning number", title="1er Numero Ganador")]
    num_2: Annotated[int, Field(ge=2, le=36, description="Second winning number", title="2do Numero Ganador")]
    num_3: Annotated[int, Field(ge=3, le=37, description="Third winning number", title="3er Numero Ganador")]
    num_4: Annotated[int, Field(ge=4, le=38, description="Fourth winning number", title="4to Numero Ganador")]
    num_5: Annotated[int, Field(ge=5, le=39, description="Fifth winning number", title="5to Numero Ganador")]
    accumulated: AccumulatedField = settings.baloto_settings.miloto_min_jackpot
    hits_2: ResultDetailsSchema | None = Field(
        default=None, description="2-hit prize distribution", title="Detalles de 2 Aciertos"
    )

    @model_validator(mode="after")
    def check_ascending(self) -> Self:
        numbers = [self.num_1, self.num_2, self.num_3, self.num_4, self.num_5]
        self._validate_ascending(numbers)
        return self

    def calculate_combination_id(self) -> str:
        return numbers_to_hex(
            self.num_1, self.num_2, self.num_3, self.num_4, self.num_5, settings.baloto_settings.miloto_max_num
        )

    @computed_field
    @property
    def full_spanish_date(self) -> str:
        """The draw date formatted as a full Spanish string.

        :return: The formatted date, for example ``"Lunes, 27 de Julio de 2026"``.
        """
        return full_date(self.game_date)
