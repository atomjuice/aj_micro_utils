import pytest
import uuid

from tortoise.contrib.test import initializer

from aj_micro_utils.tests.conftest import unpack_nested_filters
from aj_micro_utils.tests.test_models import TestModel
from aj_micro_utils.search_and_filter.queries import (
    get_search_fields,
    get_search_q,
    get_orm_lookup,
    field_exists,
    get_filter_q,
)

from tortoise.query_utils import Q


@pytest.mark.parametrize(
    "input, expected",
    [
        (str(uuid.uuid4()), ["CharField", "UUIDField"]),
        ("true", ["CharField", "BooleanField"]),
        ("false", ["CharField", "BooleanField"]),
        ("some phrase", ["CharField"]),
        (
            "5",
            [
                "CharField",
                "IntField",
                "SmallIntField",
                "FloatField",
                "IntEnumFieldInstance",
            ],
        ),
        ("325584", ["CharField", "IntField", "FloatField"]),
        ("325.23", ["CharField", "FloatField"]),
    ],
)
def test_get_search_fields(input, expected):
    assert get_search_fields(input).sort() == expected.sort()


@pytest.mark.parametrize(
    "input, expected",
    [
        ("yo", ["model_name", "email", "reference"]),
        (str(uuid.uuid4()), ["model_name", "email", "reference", "uuid_field"]),
    ],
)
def test_get_search_q(input, expected):
    q = get_search_q(TestModel, input)

    for filter in unpack_nested_filters(q):
        for key in filter.keys():
            assert key in expected


@pytest.mark.parametrize(
    "field, graphql_lookup, expected",
    [
        ("model_name", {"eq": "something"}, {"model_name": "something"}),
        ("reference", {"matches": "something"}, {"reference__iexact": "something"}),
        ("tracking_number", {"gte": 2}, {"tracking_number__gte": 2}),
        (
            "tracking_number",
            {"gte": 2, "lt": 500, "gt": 300},
            {
                "tracking_number__gte": 2,
                "tracking_number__lt": 500,
                "tracking_number__gt": 300,
            },
        ),
        ("tracking_number", {"gte": 2}, {"tracking_number__gte": 2}),
    ],
)
def test_get_orm_lookup(field, graphql_lookup, expected):
    assert get_orm_lookup(field, graphql_lookup) == expected


@pytest.mark.parametrize(
    "model, field_name, expected",
    [
        (TestModel, "reference", True),
        (TestModel, "model_name", True),
        (TestModel, "email", True),
        (TestModel, "id", True),
        (TestModel, "tracking_number", True),
        (TestModel, "uuid_field", True),
        (TestModel, "wrong_field", False),
        (TestModel, "whatever", False),
    ],
)
def test_field_exists(model, field_name, expected):
    assert field_exists(model, field_name) == expected


@pytest.mark.parametrize(
    "model, filter, expected",
    [
        (TestModel, {"modelName": {"eq": "something"}}, ["model_name"]),
        (
            TestModel,
            {"modelName": {"eq": "something"}, "trackingNumber": {"gt": 2}},
            ["model_name", "tracking_number__gt"],
        ),
        (
            TestModel,
            {
                "modelName": {"matches": "something"},
                "trackingNumber": {"gt": 2},
                "id": {"lt": 3},
                "id": {"lte": 3},
                "id": {"gte": 3},
            },
            [
                "model_name__iexact",
                "tracking_number__gt",
                "id__lt",
                "id__gte",
                "id__lte",
            ],
        ),
    ],
)
def test_get_filter_q(model, filter, expected):
    q = get_filter_q(model, filter)
    for filter in unpack_nested_filters(q):
        for key in filter.keys():
            assert key in expected


def test_search_func_in_resolver(
    initialize_tests,
    initialize_model_resolver,
):
    search = {"search": "some search term"}
    expected_qs = TestModel.filter(
        Q(
            Q(model_name="some search term"),
            Q(email="some search term"),
            Q(reference="some search term"),
            join_type="OR",
        )
    ).distinct()

    initialize_model_resolver.extra = search

    qs = initialize_model_resolver.query_set()

    assert expected_qs.sql() == qs.sql()


def test_filter_func_in_resolver(
    initialize_tests,
    initialize_model_resolver,
):
    filter = {
        "filter": {
            "modelName": {"eq": "some filter"},
            "trackingNumber": {"gt": 2},
        }
    }
    expected_qs = TestModel.filter(
        Q(
            Q(model_name="some filter"),
            Q(tracking_number__gt=2),
            join_type="AND",
        )
    ).distinct()

    initialize_model_resolver.extra = filter

    qs = initialize_model_resolver.query_set()

    assert expected_qs.sql() == qs.sql()


def test_base_qs_in_resolver(
    initialize_tests,
    initialize_model_resolver,
):
    expected_qs = TestModel.all()

    qs = initialize_model_resolver.query_set()

    assert expected_qs.sql() == qs.sql()


def test_get_data(
    initialize_tests,
    created_data,
    initialize_model_resolver,
    event_loop,
):
    data = event_loop.run_until_complete(initialize_model_resolver.get_data())

    assert len(data["edges"]) == 10
