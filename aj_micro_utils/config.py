from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    jwt_gateway_secret: str
    graphql_url: str = "https://debug.graphql.atomjuice.io/"
    graphql_token: str = ""
    git_version: str = "v0.1"
    debug: bool = False
    database_url: str = ""
    sentinel: bool = False

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
