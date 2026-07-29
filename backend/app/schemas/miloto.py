"""
Define validation and presentation schemas for MiLoto draw results.

The module validates MiLoto winning-number combinations, accumulated prizes,
and payout details. It also generates stable combination identifiers and exposes
formatted draw-date information for API responses and downstream consumers.
"""

from typing import Annotated, Self

from pydantic import ConfigDict, Field, computed_field, model_validator

from app.config.app_settings import settings
from app.schemas.base import AccumulatedField, BalotoMilotoBaseShema, ResultDetailsSchema
from app.utils.date_utils import full_date
from app.utils.math_utils import numbers_to_hex


class MilotoResultSchema(BalotoMilotoBaseShema):
    """
    Represent a validated MiLoto result used by the application.

    The schema validates draw metadata, ordered winning numbers, accumulated
    prizes, and payout details. It also exposes computed values such as the stable
    combination identifier and formatted draw-date representations used in API
    responses.
    """

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
        """
        Validate that MiLoto winning numbers are unique and strictly ascending.

        :return: The validated MiLoto result instance.
        :raises ValueError: If the winning numbers are duplicated or not in ascending order.
        """
        numbers = [self.num_1, self.num_2, self.num_3, self.num_4, self.num_5]
        self._validate_ascending(numbers)
        return self

    def calculate_combination_id(self) -> str:
        """
        Generate the stable identifier for the MiLoto winning combination.

        :return: The hexadecimal identifier derived from the ordered winning numbers.
        """
        return numbers_to_hex(
            (self.num_1, self.num_2, self.num_3, self.num_4, self.num_5), settings.baloto_settings.miloto_max_num
        )

    @computed_field
    @property
    def full_spanish_date(self) -> str:
        """
        The draw date formatted as a full Spanish string.

        :return: The formatted date, for example ``"Lunes, 27 de Julio de 2026"``.
        """
        return full_date(self.game_date)
