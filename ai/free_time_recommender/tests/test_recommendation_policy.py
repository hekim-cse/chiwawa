from typing import cast

import pytest

from ai.free_time_recommender.domain.recommendation_policy import (
    RecommendationPolicy,
)


# 유효한 추천 정책 생성 헬퍼
def build_policy(
    *,
    minimum_stay_minutes: int = 60,
    maximum_one_way_travel_minutes: int = 20,
    maximum_distance_meters: int = 3000,
    candidate_limit: int = 10,
    allowed_categories: tuple[str, ...] = (
        "cafe",
        "park",
    ),
) -> RecommendationPolicy:
    return RecommendationPolicy(
        minimum_stay_minutes=minimum_stay_minutes,
        maximum_one_way_travel_minutes=maximum_one_way_travel_minutes,
        maximum_distance_meters=maximum_distance_meters,
        candidate_limit=candidate_limit,
        allowed_categories=allowed_categories,
    )

# 테스트 케이스
def test_recommendation_policy_accepts_valid_values() -> None:
    policy = build_policy()

    assert policy.minimum_stay_minutes == 60
    assert policy.maximum_one_way_travel_minutes == 20
    assert policy.maximum_distance_meters == 3000
    assert policy.candidate_limit == 10
    assert policy.allowed_categories == (
        "cafe",
        "park",
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_stay_minutes",
        "candidate_limit",
    ],
)
def test_positive_integer_fields_reject_zero(
    field_name: str,
) -> None:
    values = {
        "minimum_stay_minutes": 60,
        "candidate_limit": 10,
    }
    values[field_name] = 0

    with pytest.raises(
        ValueError,
        match=f"{field_name}는 1 이상이어야 합니다.",
    ):
        build_policy(**values)


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_stay_minutes",
        "candidate_limit",
    ],
)
def test_positive_integer_fields_reject_negative_value(
    field_name: str,
) -> None:
    values = {
        "minimum_stay_minutes": 60,
        "candidate_limit": 10,
    }
    values[field_name] = -1

    with pytest.raises(
        ValueError,
        match=f"{field_name}는 1 이상이어야 합니다.",
    ):
        build_policy(**values)


@pytest.mark.parametrize(
    "field_name",
    [
        "maximum_one_way_travel_minutes",
        "maximum_distance_meters",
    ],
)
def test_non_negative_integer_fields_accept_zero(
    field_name: str,
) -> None:
    values = {
        "maximum_one_way_travel_minutes": 20,
        "maximum_distance_meters": 3000,
    }
    values[field_name] = 0

    policy = build_policy(**values)

    assert getattr(policy, field_name) == 0


@pytest.mark.parametrize(
    "field_name",
    [
        "maximum_one_way_travel_minutes",
        "maximum_distance_meters",
    ],
)
def test_non_negative_integer_fields_reject_negative_value(
    field_name: str,
) -> None:
    values = {
        "maximum_one_way_travel_minutes": 20,
        "maximum_distance_meters": 3000,
    }
    values[field_name] = -1

    with pytest.raises(
        ValueError,
        match=f"{field_name}는 0 이상이어야 합니다.",
    ):
        build_policy(**values)


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_stay_minutes",
        "maximum_one_way_travel_minutes",
        "maximum_distance_meters",
        "candidate_limit",
    ],
)
def test_integer_fields_reject_boolean(
    field_name: str,
) -> None:
    values = {
        "minimum_stay_minutes": 60,
        "maximum_one_way_travel_minutes": 20,
        "maximum_distance_meters": 3000,
        "candidate_limit": 10,
    }
    values[field_name] = True

    with pytest.raises(
        TypeError,
        match=f"{field_name}는 정수여야 합니다.",
    ):
        build_policy(**values)


@pytest.mark.parametrize(
    "field_name",
    [
        "minimum_stay_minutes",
        "maximum_one_way_travel_minutes",
        "maximum_distance_meters",
        "candidate_limit",
    ],
)
def test_integer_fields_reject_non_integer(
    field_name: str,
) -> None:
    values = {
        "minimum_stay_minutes": 60,
        "maximum_one_way_travel_minutes": 20,
        "maximum_distance_meters": 3000,
        "candidate_limit": 10,
    }
    values[field_name] = 1.5

    with pytest.raises(
        TypeError,
        match=f"{field_name}는 정수여야 합니다.",
    ):
        build_policy(**values)


def test_allowed_categories_rejects_non_tuple() -> None:
    with pytest.raises(
        TypeError,
        match="tuple이어야 합니다",
    ):
        build_policy(
            allowed_categories=cast(
                tuple[str, ...],
                ["cafe", "park"],
            ),
        )


def test_allowed_categories_rejects_empty_tuple() -> None:
    with pytest.raises(
        ValueError,
        match="1개 이상의 카테고리",
    ):
        build_policy(
            allowed_categories=(),
        )


def test_allowed_categories_rejects_blank_value() -> None:
    with pytest.raises(
        ValueError,
        match="빈 문자열",
    ):
        build_policy(
            allowed_categories=(
                "cafe",
                "   ",
            ),
        )


def test_allowed_categories_rejects_non_string_value() -> None:
    with pytest.raises(
        TypeError,
        match="각 값은 문자열",
    ):
        build_policy(
            allowed_categories=cast(
                tuple[str, ...],
                (
                    "cafe",
                    1,
                ),
            ),
        )


def test_allowed_categories_rejects_duplicate_value() -> None:
    with pytest.raises(
        ValueError,
        match="중복 값",
    ):
        build_policy(
            allowed_categories=(
                "cafe",
                "cafe",
            ),
        )


def test_allowed_categories_preserves_input_values() -> None:
    policy = build_policy(
        allowed_categories=(
            "Cafe",
            " cafe ",
        ),
    )

    assert policy.allowed_categories == (
        "Cafe",
        " cafe ",
    )
