import redis.asyncio as redis


class RedisPool:
    def __init__(self, host: str, port: int, db: int):
        self._pool = redis.ConnectionPool(host=host, port=port, db=db)
        self.client = redis.Redis(connection_pool=self._pool)

    async def get_connection(self):
        return redis.Redis(connection_pool=self._pool)
