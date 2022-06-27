from ariadne import convert_camel_case_to_snake
from enum import Enum
from tortoise import models, queryset
from typing import List, Optional
from aj_micro_utils.paginator import RelayPaginator
from aj_micro_utils.util import validate_uuid4
from tortoise.query_utils import Q


class ModelResolver:
    """
    Model resolver class that creates base query of the given model
    Uses the Relay Paginator
    Accepts filter and search dictionaires that contain ORM lookups
    """

    def __init__(self, model, formatter, **kwargs) -> None:
        self.model = model
        self.formatter = formatter
        self.extra = kwargs

    @property
    def base_queryset(self) -> queryset.QuerySet:
        if self.extra.get("prefetch"):
            return self.model.all().prefetch_related(*self.extra.get("prefetch"))

        return self.model.all()

    @property
    def paginator(self) -> RelayPaginator:
        first = self.extra.get("first")
        after = self.extra.get("after")

        return RelayPaginator(
            first=first,
            after=after,
            typename=self.model.__name__,
        )

    def search_queryset(
        self, qs: queryset.QuerySet = None
    ) -> Optional[queryset.QuerySet]:
        return get_search_query(
            model=self.model, search=self.extra.get("search"), qs=qs
        )

    def filter_queryset(
        self, qs: queryset.QuerySet = None
    ) -> Optional[queryset.QuerySet]:
        return get_filter_query(
            model=self.model, filter=self.extra.get("filter"), qs=qs
        )

    def query_set(self, qs: queryset.QuerySet = None) -> queryset.QuerySet:
        if self.extra.get("search"):
            return self.search_queryset(qs=qs)
        elif self.extra.get("filter"):
            return self.filter_queryset(qs=qs)

        return qs if qs else self.base_queryset

    async def get_data(self, qs: queryset.QuerySet = None) -> dict:
        return await self.paginator.paginate(
            data_query=self.query_set(qs=qs if qs else self.base_queryset),
            formatter=self.formatter,
        )


def get_search_query(
    model: models.Model,
    search: str,
    qs: queryset.QuerySet = None,
) -> queryset.QuerySet:
    if qs:
        return qs.filter(get_search_q(model, search)).distinct()
    return model.filter(get_search_q(model, search)).distinct()


def get_filter_query(
    model: models.Model,
    filter: dict,
    qs: queryset.QuerySet = None,
) -> queryset.QuerySet:
    if qs:
        return qs.filter(get_filter_q(model, filter)).distinct()
    return model.filter(get_filter_q(model, filter)).distinct()


def get_filter_q(
    model: models.Model,
    filter: dict,
) -> Q:

    filters = Q()
    for key, val in filter.items():
        formatted_field_name = convert_camel_case_to_snake(key)
        assert field_exists(model, formatted_field_name)
        filters &= Q(**get_orm_lookup(formatted_field_name, val))
    return filters


def field_exists(model: models.Model, field_name: str) -> bool:
    model_desc = model.describe()

    if model_desc["pk_field"]["name"] == field_name:
        return True
    for data_field in model_desc["data_fields"]:
        if data_field["name"] == field_name:
            return True
    return False


def get_orm_lookup(key, value):
    orm_lookups = {}
    if isinstance(value, dict):
        for k, v in value.items():
            mapping = str(key) + GRAPHQL_ORM_LOOKUPS[k]
            orm_lookups[mapping] = v
    else:
        orm_lookups[key] = value
    return orm_lookups


GRAPHQL_ORM_LOOKUPS = {
    "eq": "",
    "neq": "__not",
    "gt": "__gt",
    "lt": "__lt",
    "gte": "__gte",
    "lte": "__lte",
    "in": "__in",
    "matches": "__iexact",
    "icontains": "__icontains",
    "contains": "__contains",
}

SMALL_INT_LOWER = -32768
SMALL_INT_UPPER = 32767


def get_search_q(model: models.Model, search: str) -> Q:
    """
    Creates Q object with the fields that might contain the search value

    :param search: search term
    :return: Q object
    """
    model_desc = model.describe()
    q = Q()

    search_fields = get_search_fields(search)

    if model_desc["pk_field"]["field_type"] in search_fields:
        q |= Q(**{model_desc["pk_field"]["name"]: search})

    for data_field in model_desc["data_fields"]:
        if data_field["field_type"] in search_fields:
            max_length = data_field["constraints"].get("max_length")
            if max_length and max_length < len(search):
                continue
            q |= Q(**{data_field["name"]: search})
    return q


def get_search_fields(search: str) -> List[str]:
    """
    Depending on the type of the search term it will
    create a list of the possible Fields that might
    contain the search value

    :param search: search term
    :return: List of Field string representation
    """
    search_types = []

    for field in field_types[SearchType.CHAR]:
        search_types.append(field)

    if search.isdigit():
        if SMALL_INT_LOWER <= int(search) <= SMALL_INT_UPPER:
            for field in field_types[SearchType.SMALL_INT]:
                search_types.append(field)

        for field in field_types[SearchType.DIGIT]:
            search_types.append(field)
    if search.isdecimal():
        for field in field_types[SearchType.DECIMAL]:
            search_types.append(field)
    if validate_uuid4(search):
        for field in field_types[SearchType.UUID]:
            search_types.append(field)

    if search == "true" or search == "false":
        for field in field_types[SearchType.BOOL]:
            search_types.append(field)

    return search_types


class SearchType(str, Enum):
    DIGIT = "digit"
    DECIMAL = "decimal"
    CHAR = "char"
    UUID = "uuid"
    BOOL = "bool"
    SMALL_INT = "small_int"


field_types = {
    SearchType.CHAR: [
        "CharField",
    ],
    SearchType.DIGIT: [
        "IntField",
    ],
    SearchType.DECIMAL: [
        "FloatField",
    ],
    SearchType.UUID: [
        "UUIDField",
    ],
    SearchType.SMALL_INT: [
        "IntEnumFieldInstance",
        "SmallIntField",
    ],
    SearchType.BOOL: [
        "BooleanField",
    ],
}
