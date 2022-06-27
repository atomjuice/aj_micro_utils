import asyncio
import pytest
import uuid
from aj_micro_utils.search_and_filter.queries import ModelResolver
from aj_micro_utils.config import get_settings
from aj_micro_utils.search_and_filter.queries import ModelResolver
from aj_micro_utils.tests.test_models import TestModel, formatter
from typing import List
from tortoise.contrib.test import finalizer, initializer
from tortoise.query_utils import Q


@pytest.fixture(scope="function", autouse=True)
def initialize_tests(event_loop, request):
    db_url = get_settings().database_url
    initializer(
        ["aj_micro_utils.tests.test_models"],
        db_url=db_url,
        loop=event_loop,
    )
    request.addfinalizer(finalizer)


@pytest.fixture(scope="module")
def event_loop():
    """Change event_loop fixture to module level."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def initialize_model_resolver():
    return ModelResolver(
        TestModel,
        formatter,
    )


@pytest.fixture
def created_data(event_loop):
    for i in range(10):
        event_loop.run_until_complete(
            TestModel.create(
                model_name=f"name {i}",
                email=f"email{i}@test.com",
                reference=f"reference {i}",
                tracking_number=i,
                uuid_field=uuid.uuid4(),
            )
        )


def unpack_nested_filters(q_object: Q) -> List[dict]:
    return helper_unpack(q_object, [])


def helper_unpack(q_object: Q, filters: List):
    if q_object.children is None:
        return
    for item in q_object.children:
        if item.filters != {}:
            filters.append(item.filters)
        helper_unpack(item, filters)
    return filters
