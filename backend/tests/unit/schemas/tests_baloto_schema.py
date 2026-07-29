"""
Verify Baloto and Revancha schema validation and computed behavior.

The module covers valid model construction, field constraints, date parsing,
number ordering, accumulated-prize rules, payout details, type discrimination,
and combination identifiers for both Baloto and Revancha result schemas.
"""

from datetime import date
from typing import TYPE_CHECKING

import pytest
from app.config.app_settings import settings
from app.schemas.baloto import BalotoResultSchema, RevanchaResultSchema
from app.schemas.base import ResultDetailsSchema
from pydantic import ValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    type BalotoSchema = BalotoResultSchema | RevanchaResultSchema

# region Helper data

a_date = date(2026, 7, 25)
baloto_default_accumulated = settings.baloto_settings.baloto_min_jackpot
updates: dict[str, ResultDetailsSchema] = {
    "hits_sb": ResultDetailsSchema(prize_for_winner=10_000, winners=50),
    "hits_2_sb": ResultDetailsSchema(prize_for_winner=20_000, winners=25),
    "hits_3": ResultDetailsSchema(prize_for_winner=30_000, winners=20),
    "hits_3_sb": ResultDetailsSchema(prize_for_winner=50_000, winners=10),
    "hits_4": ResultDetailsSchema(prize_for_winner=80_000, winners=5),
    "hits_4_sb": ResultDetailsSchema(prize_for_winner=1_000_000, winners=5),
    "hits_5": ResultDetailsSchema(prize_for_winner=10_000_000, winners=2),
    "hits_5_sb": ResultDetailsSchema(prize_for_winner=10_000_000_000, winners=1),
}

# endregion


# region Module fixtures


@pytest.fixture(name="schema", scope="module", autouse=True)
def baloto_revancha_schema(br_factory: Callable[..., BalotoSchema]) -> BalotoSchema:
    """Fixture that returns a valid basic type BalotoSchema instance."""
    return br_factory(gid=1, dte=a_date, n1=5, n2=12, n3=18, n4=25, n5=33, ba=7)


# endregion


# region Module Tests


@pytest.mark.unit
def test_valid_draw_with_all_fields(schema: BalotoSchema) -> None:
    """
    Verify a fully valid BalotoResultModel is constructed correctly.

    Checks every field holds the expected value, including optional
    hit details and the private _type attribute.
    """
    # Creates a copy of the model to bypass frozen=True
    model = schema.model_copy(update=updates, deep=True)
    expected_type = "B" if isinstance(schema, BalotoResultSchema) else "R"
    cls_name = schema.__class__.__name__

    assert model.game_id == 1, "Unexpected 'game_id' value."
    assert model.game_date == a_date, "Unexpected 'game_date' value."
    assert model.num_1 == 5, "Unexpected 'num_1' value."
    assert model.num_5 == 33, "Unexpected 'num_5' value."
    assert model.balota == 7, "Unexpected 'balota' value."
    assert model.accumulated == baloto_default_accumulated, "Unexpected 'accumulated' value."
    assert model.hits_sb is not None, "Expected 'hits_sb' to be set."
    assert model.hits_sb.prize_for_winner == 10_000, "Unexpected 'hits_sb.prize_for_winner' value."
    assert model.hits_5 is not None, "Expected 'hits_5' to be set."
    assert model.hits_5.winners == 2, "Unexpected 'hits_5.winners' value."
    assert model.hits_5_sb is not None, "Expected 'hits_5_sb' to be set."
    assert model.type == expected_type, f"Unexpected '_type' for {cls_name}."


@pytest.mark.unit
def test_valid_draw_minimal_fields(schema: BalotoSchema) -> None:
    """
    Verify BalotoResultModel constructs with only required fields.

    Omits all optional hit details to ensure defaults are None
    and accumulated defaults to 0.
    """
    assert schema.accumulated == baloto_default_accumulated, "Unexpected default 'accumulated'."
    assert schema.hits_sb is None, "Expected 'hits_sb' default to None."
    assert schema.hits_2_sb is None, "Expected 'hits_2_sb' default to None."
    assert schema.hits_3 is None, "Expected 'hits_3' default to None."
    assert schema.hits_3_sb is None, "Expected 'hits_3_sb' default to None."
    assert schema.hits_4 is None, "Expected 'hits_4' default to None."
    assert schema.hits_4_sb is None, "Expected 'hits_4_sb' default to None."
    assert schema.hits_5 is None, "Expected 'hits_5' default to None."
    assert schema.hits_5_sb is None, "Expected 'hits_5_sb' default to None."


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
    br_factory: Callable[..., BalotoSchema], num_1: int, num_2: int, num_3: int, num_4: int, num_5: int
) -> None:
    """
    Verify that any pair of duplicate winning numbers raises ValueError.

    Checks all adjacent-position duplicate scenarios. The model validator
    must reject these before construction completes.
    """
    with pytest.raises(ValueError, match="unique"):
        br_factory(gid=1, dte=a_date, n1=num_1, n2=num_2, n3=num_3, n4=num_4, n5=num_5, ba=7)


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
    br_factory: Callable[..., BalotoSchema], num_1: int, num_2: int, num_3: int, num_4: int, num_5: int
) -> None:
    """
    Verify that non-ascending number sequences raise ValueError.

    Tests out-of-order positions while keeping numbers within individual
    range constraints, isolating the ascending-order validator.
    """
    with pytest.raises(ValidationError, match="ascending"):
        br_factory(gid=1, dte=a_date, n1=num_1, n2=num_2, n3=num_3, n4=num_4, n5=num_5, ba=7)


@pytest.mark.unit
@pytest.mark.parametrize(
    ("num_1", "num_2", "num_3", "num_4", "num_5", "ex_field", "ex_input", "ex_type"),
    [
        pytest.param(0, 12, 18, 25, 33, "num_1", 0, "greater_than_equal", id="num_1_below_1"),
        pytest.param(5, 12, 18, 25, 44, "num_5", 44, "less_than_equal", id="num_5_above_43"),
    ],
)
def test_numbers_outside_range_raise_error(
    br_factory: Callable[..., BalotoSchema],
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
    Verify that numbers outside the 1-43 range raise ValidationError.

    Baloto num_5 max is 43 (baloto_max_num). Covers low boundary (0)
    and high boundary (44).
    """
    with pytest.raises(ValidationError) as exc_info:
        br_factory(gid=1, dte=a_date, n1=num_1, n2=num_2, n3=num_3, n4=num_4, n5=num_5, ba=7)

    errors = exc_info.value.errors()
    error = next(e for e in errors if ex_field in e["loc"])
    assert error.get("input") == ex_input, "Unexpected 'error.input' value."
    assert error.get("type") == ex_type, "Unexpected 'error.type' value."
    assert any(ex_field in e["loc"] for e in errors), "Unexpected error on 'error.loc' value."


@pytest.mark.unit
@pytest.mark.parametrize("balota", [pytest.param(0, id="balota_below_1"), pytest.param(17, id="balota_above_16")])
def test_balota_out_of_range_raises_error(br_factory: Callable[..., BalotoSchema], balota: int) -> None:
    """
    Verify that balota outside 1-16 raises ValidationError.

    Balota has an independent range constraint (1-16) separate from
    the five main numbers.
    """
    with pytest.raises(ValidationError) as exc_info:
        br_factory(gid=1, dte=a_date, n1=5, n2=12, n3=18, n4=25, n5=33, ba=balota)

    errors = exc_info.value.errors()
    assert any("balota" in e["loc"] for e in errors), "Expected error on 'balota' field."


@pytest.mark.unit
@pytest.mark.parametrize("accumulated", [pytest.param(-1, id="negative"), pytest.param(0, id="below_minimum")])
def test_accumulated_raises_error(schema: BalotoResultSchema, accumulated: int) -> None:
    """
    Verify that negative accumulated raises ValidationError.

    Accumulated prize must be non-negative per Field(ge=0).
    """
    model_dump = schema.model_dump()
    model_dump["accumulated"] = accumulated
    with pytest.raises(ValidationError) as exc_info:
        BalotoResultSchema(**model_dump)

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
        pytest.param(40, 41, 42, 43, 43, "num_1", 40, "less_than_equal", id="num_1_above_39"),
        pytest.param(1, 2, 3, 4, 4, "num_5", 4, "greater_than_equal", id="num_5_below_5"),
        pytest.param(1, 1, 3, 42, 43, "num_2", 1, "greater_than_equal", id="num_2_below_2"),
        pytest.param(5, 12, 42, 43, 43, "num_3", 42, "less_than_equal", id="num_3_above_41"),
        pytest.param(5, 12, 18, 43, 43, "num_4", 43, "less_than_equal", id="num_4_above_42"),
    ],
)
def test_position_range_violation(
    br_factory: Callable[..., BalotoSchema],
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
    Verify per-position range constraints for Baloto.

    Each position has a tighter range to ensure ascending order:
    num_1 in [1,39], num_2 in [2,40], num_3 in [3,41], num_4 in [4,42], num_5 in [5,43].
    """
    with pytest.raises(ValidationError) as exc_info:
        br_factory(gid=1, dte=a_date, n1=num_1, n2=num_2, n3=num_3, n4=num_4, n5=num_5, ba=7)

    errors = exc_info.value.errors()
    assert any(ex_field in e["loc"] for e in errors), "Unexpected 'error.loc' value."
    error = next(e for e in errors if ex_field in e["loc"])
    assert error.get("input") == ex_input, "Unexpected 'error.input' value."
    assert error.get("type") == ex_type, "Unexpected 'error.type' value."


@pytest.mark.unit
def test_has_correct_type(schema: BalotoSchema) -> None:
    """
    Verify RevanchaResultModel has _type == 'R' and BalotoResultModel has _type "B".

    The only behavioral difference from BalotoResultModel is the
    private _type attribute. Field validation is inherited from
    _SharedBalotoRevanchaResultSchema and tested via Baloto tests.
    """
    if isinstance(schema, RevanchaResultSchema):
        assert schema.type == "R", "Unexpected '_type' for RevanchaResultSchema."
    else:
        assert schema.type == "B", "Unexpected '_type' for BalotoResultSchema."


@pytest.mark.unit
def test_game_date_type_error_on_invalid_type(br_factory: Callable[..., BalotoSchema]) -> None:
    """
    Verify TypeError raised when game_date is not str or date.

    Covers base.py line 31-32: the else branch of the type check
    in parse_spanish_date validator.
    """
    with pytest.raises(ValidationError) as exc_info:
        br_factory(gid=1, dte="012345", n1=5, n2=12, n3=18, n4=25, n5=33, ba=7)

    assert exc_info.value.error_count() == 1, "Unxpected 'error_count' value"
    error = exc_info.value.errors()[0]
    assert error["type"] == "value_error", "Unexpected 'error.type' value"
    assert "Invalid Spanish date" in error["msg"], "Unexpected 'error.type' value"

    data = br_factory(gid=1, dte=a_date, n1=5, n2=12, n3=18, n4=25, n5=33, ba=7)
    model_dict = data.model_dump()
    model_dict["game_date"] = 12345
    with pytest.raises(TypeError, match="game_date must be a Spanish date string"):
        BalotoResultSchema(**model_dict)


# endregion
