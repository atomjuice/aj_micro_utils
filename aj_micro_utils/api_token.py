from typing import Union

from pydantic import BaseModel

from aj_micro_utils.cache import gql_query_cache


class AccountId(BaseModel):
    id: str


class ApiToken(BaseModel):
    id: int
    account: AccountId
    feedId: int
    token: str
    service: str
    created: str


async def validate(token: str, service: str, client_name: str) -> Union[ApiToken, bool]:
    response = await gql_query_cache(
        f"api-token-{token}",
        """
        query validateAPITokenMutation($token: String!, $service: String!) {
            validateAPIToken(token: $token, service: $service) {
                success
                token {
                    id
                    account {
                        id
                    }
                    feedId
                    token
                    service
                    created
                }
            }
        }
        """,
        {"token": token, "service": service},
        client_name,
    )

    data = response["data"]["validateAPIToken"]

    if data is None:
        return False

    token = data.get("token")

    if token:
        return ApiToken(**token)

    return False
