import aioredis
from aioredis.sentinel import SentinelPool
from aioredis.sentinel.pool import ManagedPool


class RedisSentinel:
    _sentinel_pool: SentinelPool = None

    @classmethod
    async def setup(cls, sentinals):
        cls._sentinel_pool = await aioredis.sentinel.create_sentinel_pool(sentinals)

    @classmethod
    async def shutdown(cls):
        cls._sentinel_pool.close()
        await cls._sentinel_pool.wait_closed()

    @classmethod
    async def _master(cls) -> ManagedPool:
        return cls._sentinel_pool.master_for("mymaster")

    @classmethod
    async def _slave(cls) -> ManagedPool:
        return cls._sentinel_pool.slave_for("mymaster")

    @classmethod
    async def get(cls, key) -> object:
        pool: ManagedPool = await cls._slave()

        async with pool.get() as conn:
            return await conn.execute("get", key)

    @classmethod
    async def set(cls, key, value, ex: int = 3600):
        pool: ManagedPool = await cls._master()

        async with pool.get() as conn:
            return await conn.execute("setex", key, ex, value)

    @classmethod
    async def exists(cls, key):
        pool: ManagedPool = await cls._slave()

        async with pool.get() as conn:
            return await conn.execute("exists", key)

    @classmethod
    async def delete(cls, key):
        pool: ManagedPool = await cls._master()

        async with pool.get() as conn:
            exists = await conn.execute("exists", key)

            if exists:
                return await conn.execute("del", key)

            return False


class Redis:
    _pool: aioredis.Redis = None

    @classmethod
    async def setup(cls, dsn):
        cls._pool = await aioredis.create_redis_pool(dsn)

    @classmethod
    async def get(cls, key):
        return await cls._pool.get(key)

    @classmethod
    async def set(cls, key, value, ex: int = 3600):
        return await cls._pool.set(key, value, expire=ex)

    @classmethod
    async def exists(cls, key):
        return await cls._pool.exists(key)

    @classmethod
    async def delete(cls, key):
        exists = await cls._pool.exists(key)

        if exists:
            return await cls._pool.delete(key)

        return False

    @classmethod
    async def shutdown(cls):
        cls._pool.close()
        await cls._pool.wait_closed()
