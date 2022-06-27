import json
from datetime import datetime, date
from decimal import Decimal
from functools import _make_key
from uuid import UUID

from tortoise.queryset import QuerySet

from aj_micro_utils.config import get_settings
from aj_micro_utils.db import run_query_with_pagination
from aj_micro_utils.helper import gql_query
from aj_micro_utils.redis import Redis, RedisSentinel

SENTINEL = get_settings().sentinel


class MyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, UUID):
            return str(o)

        if isinstance(o, Decimal):
            return float(o)

        if isinstance(o, datetime):
            return str(o)

        if isinstance(o, date):
            return str(o)

        return super(MyEncoder, self).default(o)


async def redis_get(key):
    if SENTINEL:
        return await RedisSentinel.get(key)

    return await Redis.get(key)


async def redis_set(key, value, ex: int = 3600):
    if SENTINEL:
        return await RedisSentinel.set(key, value, ex)

    return await Redis.set(key, value, ex)


async def redis_exists(key):
    if SENTINEL:
        return await RedisSentinel.exists(key)

    return await Redis.exists(key)


async def redis_update(key, value, ex: int = 3600):
    if await redis_exists(key):
        await redis_set(key, value, ex)

        return True

    return False


async def redis_delete(key):
    if SENTINEL:
        return await RedisSentinel.delete(key)

    return await Redis.delete(key)


async def cache_query(
    cache_key, sql, expiry: int = 3600, connection: str = "default", **kwargs
):
    cache = await redis_get(cache_key)

    if cache:
        return json.loads(cache)

    results = await run_query_with_pagination(sql, connection, **kwargs)

    await redis_set(
        cache_key, json.dumps([dict(r) for r in results], cls=MyEncoder), ex=expiry
    )

    return results


async def gql_query_cache(cache_key, query, variables, client_name, expiry: int = 3600):
    cache = await redis_get(cache_key)

    if cache:
        return json.loads(cache)

    response = await gql_query(
        query,
        variables,
        client_name,
    )

    if response["data"] is None:
        return await gql_query_cache(cache_key, query, variables, client_name, expiry)

    await redis_set(cache_key, json.dumps(response, cls=MyEncoder), ex=expiry)

    return response


async def run_query_with_pagination_and_cache(
    sql: str,
    cursor_name: str,
    expiry: int = 3600,
    connection: str = "default",
    *args,
    **kwargs,
):
    cache_key = f"{cursor_name}_{hash(_make_key(args, kwargs, typed=False))}"

    cache = await redis_get(cache_key)

    if cache:
        return json.loads(cache)

    results = await run_query_with_pagination(sql, connection, **kwargs)

    await redis_set(
        cache_key, json.dumps([dict(r) for r in results], cls=MyEncoder), ex=expiry
    )

    return results


async def orm_query_and_cache(
    queryset: QuerySet,
    after: str,
    after_cursor,
    limit: int = 11,
    expiry: int = 3600,
    *args,
    **kwargs,
):
    cache_key = (
        f"{queryset.model.__name__}_{hash(_make_key(args, kwargs, typed=False))}"
    )

    cache = await redis_get(cache_key)

    if cache:
        return [queryset.model(**r) for r in json.loads(cache)]

    if after:
        result = (
            await queryset.filter(
                **{f"{queryset.model.Meta.paginate_on}__lt": after_cursor}
            )
            .all()
            .order_by(f"-{queryset.model.Meta.paginate_on}")
            .limit(limit)
            .values()
        )
    else:
        result = (
            await queryset.all()
            .order_by(f"-{queryset.model.Meta.paginate_on}")
            .limit(limit)
            .values()
        )

    await redis_set(cache_key, json.dumps(result, cls=MyEncoder), ex=expiry)

    return [queryset.model(**r) for r in result]


async def orm_redis_get(key: str, model, single: bool = False):
    result = await redis_get(key)

    if result:
        convert = json.loads(result)

        if single:
            return model(**convert[0])

        return [model(**r) for r in convert]

    return None


async def orm_redis_set(key: str, value, expiry: int = 3600):
    await redis_set(key, json.dumps(value, cls=MyEncoder), ex=expiry)
