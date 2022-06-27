from arq import create_pool
from arq.connections import RedisSettings

from aj_micro_utils.config import get_settings

SENTINEL = get_settings().sentinel


class Arq:
    _redis = None

    @classmethod
    async def setup(cls, dsn):
        cls._redis = await create_pool(RedisSettings.from_dsn(dsn))

    @classmethod
    async def enqueue(cls, function: str, *args, **kwargs):
        return await cls._redis.enqueue_job(function, *args, **kwargs)
