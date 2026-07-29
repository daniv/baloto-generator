from datetime import date
from typing import TYPE_CHECKING

import pytest
from backend.app.config.app_settings import settings
from backend.app.schemas.base import ResultDetailsSchema
from backend.app.schemas.miloto import MilotoResultSchema
from pydantic import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

a_date = date(2026, 7, 25)
miloto_default_accumulated = settings.baloto_settings.miloto_min_jackpot
updates: dict[str, ResultDetailsSchema | int] = {
    "accumulated": miloto_default_accumulated,
    "hits_2": ResultDetailsSchema(prize_for_winner=10_000, winners=50),
    "hits_3": ResultDetailsSchema(prize_for_winner=30_000, winners=20),
    "hits_4": ResultDetailsSchema(prize_for_winner=80_000, winners=5),
    "hits_5": ResultDetailsSchema(prize_for_winner=10_000_000, winners=2),
}


@pytest.fixture(name="schema", scope="module", autouse=True)
def miloto_schema(m_factory: Callable[..., MilotoResultSchema]) -> MilotoResultSchema:
    return m_factory(gid=1, dte=a_date, n1=5, n2=12, n3=18, n4=25, n5=33)


@pytest.mark.unit
def test_valid_draw_with_all_fields(schema: MilotoResultSchema) -> None:
    """
    Verify a fully valid MilotoResultModel is constructed correctly.

    Checks that every field (game_id, game_date, numbers, accumulated)
    holds the expected value after construction with valid data.
    """
    # Creates a copy of the model to bypass frozen=True
    model = schema.model_copy(update=updates, deep=True)

    assert model.game_id == 1, "Unexpected 'game_id' value."
    assert model.game_date == a_date, "Unexpected 'game_date' value."
    assert model.num_1 == 5, "Unexpected 'num_1' value."
    assert model.num_5 == 33, "Unexpected 'num_5' value."
    assert model.accumulated == miloto_default_accumulated, "Unexpected 'accumulated' value."
    assert model.hits_5 is not None, "Expected 'hits_5' to be set."
    assert model.hits_3 is not None, "Expected 'hits_3' to be set."
    assert model.hits_2 is not None, "Expected 'hits_2' to be set."
    assert model.hits_3.prize_for_winner == 30_000, "Unxpected 'hits_3.prize_for_winner' value."
    assert model.hits_2.winners == 50, "Unexpected 'hits_2.winners' value."


@pytest.mark.unit
@pytest.mark.parametrize(
    ("num_1", "num_2", "num_3", "num_4", "num_5"),
    [
        pytest.param(10, 10, 18, 25, 33, id="num_1_equals_num_2"),
        pytest.param(5, 12, 12, 25, 33, id="num_2_equals_num_3"),
        pytest.param(5, 12, 18, 18, 33, id="num_3_equals_num_4"),
        pytest.param(5, 12, 18, 25, 25, id="num_4_equals_num_5"),
    ],
)
def test_duplicate_numbers_raise_error(
    m_factory: Callable[..., MilotoResultSchema], num_1: int, num_2: int, num_3: int, num_4: int, num_5: int
) -> None:
    """
    Verify that any pair of duplicate winning numbers raises ValueError.

    Checks all adjacent-position duplicate scenarios (n1=n2, n2=n3, n3=n4, n4=n5).
    The model validator must reject these before construction completes.
    """
    with pytest.raises(ValueError, match="unique"):
        m_factory(gid=1, dte=a_date, n1=num_1, n2=num_2, n3=num_3, n4=num_4, n5=num_5)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("num_1", "num_2", "num_3", "num_4", "num_5"),
    [
        pytest.param(33, 12, 18, 25, 33, id="num_1_greater_than_num_2"),
        pytest.param(5, 12, 10, 25, 33, id="num_3_greater_than_num_2"),
        pytest.param(5, 12, 18, 25, 20, id="num_5_less_than_num_4"),
    ],
)
def test_non_ascending_numbers_raise_error(
    m_factory: Callable[..., MilotoResultSchema], num_1: int, num_2: int, num_3: int, num_4: int, num_5: int
) -> None:
    """
    Verify that non-ascending number sequences raise ValueError.

    Tests out-of-order positions while keeping every number within its
    individual range constraint, isolating the ascending-order validator.
    """
    with pytest.raises(ValidationError, match="ascending"):
        m_factory(gid=1, dte=a_date, n1=num_1, n2=num_2, n3=num_3, n4=num_4, n5=num_5)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("num_1", "num_2", "num_3", "num_4", "num_5", "ex_field", "ex_input", "ex_type"),
    [
        pytest.param(0, 12, 18, 25, 33, "num_1", 0, "greater_than_equal", id="num_1_below_1"),
        pytest.param(5, 12, 18, 25, 40, "num_5", 40, "less_than_equal", id="num_5_above_39"),
        pytest.param(50, 51, 52, 53, 54, "num_1", 50, "less_than_equal", id="all_above_39"),
    ],
)
def test_numbers_outside_1_to_39_raise_error(
    m_factory: Callable[..., MilotoResultSchema],
    num_1: int,
    num_2: int,
    num_3: int,
    num_4: int,
    num_5: int,
    ex_field: str,
    ex_input: int,
    ex_type: str,
) -> None:
    """
    Verify that numbers outside the 1-39 range raise ValidationError.

    Covers low boundary (0), high boundary (40), and all-out-of-range (50-54).
    ValidationError comes from Pydantic's Field(ge=1, le=39) constraints.
    """
    with pytest.raises(ValidationError) as exc_info:
        m_factory(gid=1, dte=a_date, n1=num_1, n2=num_2, n3=num_3, n4=num_4, n5=num_5)

    errors = exc_info.value.errors()
    target = [e for e in errors if ex_field in e["loc"]][0]
    assert target.get("input") == ex_input, "Unexpected error on 'error.input' value."
    assert target.get("type") == ex_type, "Unexpected error on 'error.type' value."
    assert any(ex_field in e["loc"] for e in errors), "Unexpected error on 'error.loc' value."


@pytest.mark.unit
@pytest.mark.parametrize("accumulated", [pytest.param(-1, id="negative"), pytest.param(0, id="below_minimum")])
def test_accumulated_raises_error(schema: MilotoResultSchema, accumulated: int) -> None:
    """
    Verify that negative accumulated raises ValidationError.

    Accumulated prize must be non-negative per Field(ge=0).
    """
    with pytest.raises(ValidationError) as exc_info:
        model_dump = schema.model_dump()
        model_dump["accumulated"] = accumulated
        MilotoResultSchema(**model_dump)

    errors = exc_info.value.errors()
    assert exc_info.value.error_count() == 1, "Unexpected error_count()."
    error = errors[0]
    assert error.get("input") == accumulated, "Unexpected 'error.input' value."
    assert error.get("type") == "greater_than", "Unexpected 'error.type' value."
    assert any("accumulated" in e["loc"] for e in errors), "Expected error on 'accumulated' field."


@pytest.mark.unit
@pytest.mark.parametrize(
    ("num_1", "num_2", "num_3", "num_4", "num_5", "ex_field", "ex_input", "ex_type"),
    [
        pytest.param(36, 37, 38, 39, 39, "num_1", 36, "less_than_equal", id="num_1_above_35"),
        pytest.param(1, 2, 3, 4, 4, "num_5", 4, "greater_than_equal", id="num_5_below_5"),
        pytest.param(34, 37, 38, 39, 39, "num_2", 37, "less_than_equal", id="num_2_above_36"),
    ],
)
def test_position_range_violation(
    m_factory: Callable[..., MilotoResultSchema],
    num_1: int,
    num_2: int,
    num_3: int,
    num_4: int,
    num_5: int,
    ex_field: str,
    ex_input: int,
    ex_type: str,
) -> None:
    """
    Verify per-position range constraints (num_1 âˆˆ [1,35], num_5 âˆˆ [5,39], etc.).

    Each position has a tighter range than 1-39 to ensure ascending order is
    possible. num_1 maxes at 35 and num_5 starts at 5. Tests boundary violations
    and a case where multiple positions exceed their range.
    """
    with pytest.raises(ValidationError) as exc_info:
        m_factory(gid=1, dte=a_date, n1=num_1, n2=num_2, n3=num_3, n4=num_4, n5=num_5)

    errors = exc_info.value.errors()
    assert any(ex_field in e["loc"] for e in errors), "Unexpected error 'error.loc' value."
    target = [e for e in errors if ex_field in e["loc"]][0]
    assert target.get("input") == ex_input, "Unexpected error 'error.input' value."
    assert target.get("type") == ex_type, "Unexpected error 'error.type' value."


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw_date", "expected"),
    [
        pytest.param("7 de Julio de 2026", date(2026, 7, 7), id="full_spanish_date"),
        pytest.param("25-Dic-2025", date(2025, 12, 25), id="abbreviated_date"),
    ],
)
def test_spanish_date_string_parsed_correctly(
    m_factory: Callable[..., MilotoResultSchema], raw_date: str, expected: date
) -> None:
    """
    Verify that Spanish date strings are parsed into the correct date.

    Tests full format ('7 de Julio de 2026') and abbreviated format ('25-Dic-2025')
    to cover the two common formats returned by the Playwright scraper.
    """
    model = m_factory(gid=1, dte=raw_date, n1=5, n2=12, n3=18, n4=25, n5=33)
    assert model.game_date == expected, "Unexpected 'model.game_date' value."


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw_date",
    [
        pytest.param("not a date", id="random_string"),
        pytest.param("", id="empty_string"),
        pytest.param("31-feb-2025", id="invalid date"),
    ],
)
def test_invalid_date_string_raises_error(m_factory: Callable[..., MilotoResultSchema], raw_date: str) -> None:
    """
    Verify that unparseable strings raise ValueError with a Spanish-specific message.

    Covers random text and empty string. The error message must mention
    'Invalid Spanish date' so callers can distinguish parsing failures.
    """
    with pytest.raises(ValidationError, match="Invalid Spanish date"):
        m_factory(gid=1, dte=raw_date, n1=5, n2=12, n3=18, n4=25, n5=33)


@pytest.mark.unit
def test_datetime_date_passes_through_unchanged(m_factory: Callable[..., MilotoResultSchema]) -> None:
    """
    Verify that a date object is returned as-is without parsing.

    The validator must skip parsing when the input is already a date,
    not attempt to stringify or re-parse it.
    """
    d = date(2026, 12, 25)
    model = m_factory(gid=1, dte=d, n1=5, n2=12, n3=18, n4=25, n5=33)
    assert model.game_date is d, "Unexpected 'model.game_date' type()"


@pytest.mark.unit
def test_valid_prize_details(valid_hit_details: ResultDetailsSchema) -> None:
    """
    Verify that MilotoResultDetails is constructed with non-negative values.

    Both prize_for_winner and winners must accept zero or positive integers
    and return them as provided.
    """
    assert valid_hit_details.prize_for_winner == 50_000, "Unexpected prize_for_winner value."
    assert valid_hit_details.winners == 10, "Unexpected winners value."


@pytest.mark.unit
def test_negative_prize_raises_error() -> None:
    """
    Verify that negative prize_for_winner raises ValidationError.

    The prize per winner must be non-negative (Field(ge=0)). Negative values
    are economically impossible for a prize distribution.
    """
    with pytest.raises(ValidationError) as exc_info:
        ResultDetailsSchema(prize_for_winner=-1, winners=5)

    errors = exc_info.value.errors()
    assert exc_info.value.error_count() == 1, "Unexpected error_count()"
    error = errors[0]
    assert error.get("input") == -1, "Unexpected 'error.input' value."
    assert error.get("type") == "greater_than_equal", "Unexpected error.type"
    assert any("prize_for_winner" in e["loc"] for e in errors), "Unexpected error on 'error.loc' value."
