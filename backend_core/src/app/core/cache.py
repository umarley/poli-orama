from __future__ import annotations

import asyncio
import json
import secrets
from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar, cast

from redis.asyncio import Redis

T = TypeVar("T")


class AsyncCache(Protocol):
    async def get_or_set(
        self, key: str, producer: Callable[[], Awaitable[T]]
    ) -> T: ...

    async def close(self) -> None: ...


class RedisCache:
    """Small fail-open JSON cache with a bounded single-flight wait."""

    def __init__(
        self,
        client: Redis,
        *,
        ttl: int,
        wait_seconds: float = 30.0,
        lock_seconds: int = 300,
    ) -> None:
        self.client = client
        self.ttl = ttl
        self.wait_seconds = wait_seconds
        self.lock_seconds = lock_seconds

    async def get_or_set(self, key: str, producer: Callable[[], Awaitable[T]]) -> T:
        try:
            cached = await self.client.get(key)
            if cached is not None:
                return cast(T, json.loads(cached))
        except Exception:
            return await producer()

        lock_key = f"{key}:lock"
        token = secrets.token_hex(16)
        try:
            acquired = bool(
                await self.client.set(lock_key, token, nx=True, ex=self.lock_seconds)
            )
        except Exception:
            return await producer()
        if not acquired:
            deadline = asyncio.get_running_loop().time() + self.wait_seconds
            while asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(0.05)
                try:
                    cached = await self.client.get(key)
                except Exception:
                    return await producer()
                if cached is not None:
                    return cast(T, json.loads(cached))
            return await producer()

        try:
            value = await producer()
            try:
                await self.client.set(key, json.dumps(value, ensure_ascii=False), ex=self.ttl)
            except Exception:
                pass
            return value
        finally:
            try:
                await self.client.eval(
                    """
                    if redis.call('get', KEYS[1]) == ARGV[1] then
                      return redis.call('del', KEYS[1])
                    end
                    return 0
                    """,
                    1,
                    lock_key,
                    token,
                )
            except Exception:
                pass

    async def close(self) -> None:
        try:
            await self.client.aclose()
        except Exception:
            pass


def create_redis_cache(url: str, *, ttl: int) -> RedisCache:
    return RedisCache(
        Redis.from_url(
            url,
            decode_responses=False,
            socket_connect_timeout=0.2,
            socket_timeout=0.5,
        ),
        ttl=ttl,
    )
