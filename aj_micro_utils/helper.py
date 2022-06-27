import json
import logging

import httpx
import sentry_sdk
from httpx import HTTPStatusError

from aj_micro_utils.config import get_settings

GRAPHQL_TOKEN = get_settings().graphql_token
GRAPHQL_ENDPOINT = get_settings().graphql_url
GIT_VERSION = get_settings().git_version


async def gql_query(query: str, variables: dict, client_name: str = ""):
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{GRAPHQL_ENDPOINT}graphql/",
                json={
                    "query": query,
                    "variables": variables,
                },
                headers={
                    "apollographql-client-name": client_name,
                    "apollographql-client-version": GIT_VERSION,
                    "Authorization": GRAPHQL_TOKEN,
                },
            )

            r.raise_for_status()

            return r.json()
    except HTTPStatusError as e:
        logging.error(e)
        sentry_sdk.capture_exception(e)


async def log_order_event(
    order_id: str,
    event: str,
    success: bool = True,
    data: dict = None,
    debug_data: dict = None,
):
    result = await gql_query(
        """
            mutation logOrderEventMutation ($order_id: Uuid!, $event: String!, $data: String, $debugData: String, $success: Boolean) {
                logOrderEvent(input:{
                    orderID: $order_id
                    eventSlug: $event
                    data: $data
                    debugData: $debugData
                    status: $success
                  }) {
                    success
                  }
            }
        """,
        {
            "order_id": order_id,
            "event": event,
            "data": json.dumps(data) if data else None,
            "status": success,
            "debugData": json.dumps(debug_data) if debug_data else None,
        },
    )

    return result["data"]["logOrderEvent"]["success"]
