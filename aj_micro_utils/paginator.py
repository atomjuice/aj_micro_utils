import base64
from datetime import datetime
from typing import Callable, Any, Union

from tortoise.queryset import QuerySet
from tortoise.fields import Field, DatetimeField, DateField

from aj_micro_utils import db
from aj_micro_utils.cache import (
    run_query_with_pagination_and_cache,
    orm_query_and_cache,
)
from aj_micro_utils.fields import CustomDatetimeField

PAGINATOR_MAPPING = {
    "id": """
        {% if after %}
            AND id < {{ after }}
        {% endif %}
        ORDER BY id DESC
        {% if limit %}
            LIMIT {{ limit }}
        {% endif %}
    """,
    "created": """
        {% if after %}
            AND created < {{ after }}
        {% endif %}
        ORDER BY created DESC
        {% if limit %}
            LIMIT {{ limit }}
        {% endif %}
    """,
}


class RelayPaginator:
    """Custom paginator following the Relay spec
    - only load more like type of pagination included
    - can paginate on id (int) or created (datetime)
    - typename is being used for graphql to distinguish between
    the types if union is being used
    """

    def __init__(
        self,
        first: str,
        after: str,
        typename: str,
        paginate_on: str = "id",
        use_paginate_mapping: bool = True,
        can_cache: bool = False,
        cache_time: int = 3600,
        cursor_name: str = None,
        connection: str = "default",
    ) -> None:
        if not first:
            self.first = 10
        else:
            self.first = first
        self.paginate_on = paginate_on
        self.after = after
        self.typename = typename
        self.connection = connection
        self.cursor_name = cursor_name
        self.use_paginate_mapping = use_paginate_mapping
        self.can_cache = can_cache
        self.cache_time = cache_time

    def get_relay_node_cursor(self, obj: Any, paginate_on: str) -> str:
        try:
            data = getattr(obj, paginate_on)
        except AttributeError:
            data = obj[paginate_on]

        return base64.b64encode(f"{self.cursor_name}:{data}".encode("utf-8")).decode(
            "utf-8"
        )

    def get_cursor_value(self, cursor: str) -> Any:
        """Takes the id or created out of the encoded string"""
        decoded_string = base64.b64decode(cursor).decode("utf-8")
        if self.paginate_on == "created":
            return datetime.strptime(
                decoded_string.split(":", 1)[1], "%Y-%m-%d %H:%M:%S.%f"
            )
        return int(decoded_string.split(":")[1])

    def get_orm_cursor_value(self, cursor: str, t: Field) -> Any:
        """Takes the id or created out of the encoded string"""
        decoded_string = base64.b64decode(cursor).decode("utf-8")

        if isinstance(t, CustomDatetimeField):
            return datetime.strptime(
                decoded_string.split(":", 1)[1], "%Y-%m-%d %H:%M:%S.%f%z"
            )

        if isinstance(t, DatetimeField):
            return datetime.strptime(
                decoded_string.split(":", 1)[1], "%Y-%m-%d %H:%M:%S.%f%z"
            )

        if isinstance(t, DateField):
            return datetime.strptime(decoded_string.split(":", 1)[1], "%Y-%m-%d")

        return decoded_string.split(":")[1]

    def has_next_page(self, data_length: int) -> bool:
        """Querying first + 1 rows, so if the data returned
        for ex. if 11 rows and limit is 10 then 11 > 10, so we have next page
        """
        has_next_page = False
        if data_length > self.first:
            has_next_page = True
        return has_next_page

    def map(self, query):
        if not self.use_paginate_mapping:
            return query

        return query + PAGINATOR_MAPPING[self.paginate_on]

    async def orm_query(self, queryset: QuerySet):
        if self.after:
            paginate_on_field_type = queryset.model._meta.fields_map[
                queryset.model.Meta.paginate_on
            ]
            after_cursor = self.get_orm_cursor_value(self.after, paginate_on_field_type)
        else:
            after_cursor = None

        if self.can_cache:
            return await orm_query_and_cache(
                queryset, self.after, after_cursor, (self.first + 1), self.cache_time
            )

        if self.after:
            return (
                await queryset.filter(
                    **{f"{queryset.model.Meta.paginate_on}__lt": after_cursor}
                )
                .all()
                .order_by(f"-{queryset.model.Meta.paginate_on}")
                .limit(self.first + 1)
            )

        return (
            await queryset.all()
            .order_by(f"-{queryset.model.Meta.paginate_on}")
            .limit(self.first + 1)
        )

    async def paginate(
        self, data_query: Union[str, QuerySet], formatter: Callable, **kwargs
    ) -> dict:
        """Returns rows after the last_id id if provided, if
        not returns first 10 rows
        from after, id or created is extracted, and we send it to the query
        first is the limit of the query, default is 10
        """

        is_str = isinstance(data_query, str)

        if is_str:
            if self.can_cache:
                full_results = await run_query_with_pagination_and_cache(
                    self.map(query=data_query),
                    self.cursor_name,
                    self.cache_time,
                    connection=self.connection,
                    limit=self.first + 1,  # fetching plus one row to check if next page
                    after=self.get_cursor_value(self.after)
                    if self.after
                    else None,  # after id or created
                    **kwargs,
                )
            else:
                full_results = await db.run_query_with_pagination(
                    self.map(query=data_query),
                    self.connection,
                    limit=self.first + 1,  # fetching plus one row to check if next page
                    after=self.get_cursor_value(self.after)
                    if self.after
                    else None,  # after id or created
                    **kwargs,
                )
            paginate_on = self.paginate_on
        else:
            full_results = await self.orm_query(data_query)
            paginate_on = data_query.model.Meta.paginate_on
            self.cursor_name = data_query.model.__name__

        final_results = []
        start_cursor = None
        end_cursor = None

        if len(full_results) > 0:
            final_results = full_results[: self.first]
            start_cursor = self.get_relay_node_cursor(final_results[0], paginate_on)
            end_cursor = self.get_relay_node_cursor(final_results[-1], paginate_on)

        return {
            "__typename": self.typename,
            "edges": [
                {
                    "cursor": self.get_relay_node_cursor(result, paginate_on),
                    "node": formatter(result),
                }
                for result in final_results
            ],
            "pageInfo": {
                "hasNextPage": self.has_next_page(len(full_results)),
                "startCursor": start_cursor,
                "endCursor": end_cursor,
            },
        }
