from jinjasql import JinjaSql
from tortoise import Tortoise

j = JinjaSql(param_style="asyncpg")


async def run_query_with_pagination(query: str, connection: str, **kwargs):
    """Accepts query
    and returns the appropriate data
    based on the choice:
    """
    sql = query
    query, bind_params = j.prepare_query(sql, kwargs)

    client = Tortoise.get_connection(connection)

    return await client.execute_query_dict(query, bind_params)
