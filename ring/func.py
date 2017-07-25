"""Collection of cache decorators"""

from ring.func_sync import dict  # noqa
from ring.func_sync import memcache, redis_py, redis, arcus

try:
    import asyncio
except ImportError:
    asyncio = False

__all__ = ('memcache', 'redis_py', 'redis', 'aiomcache', 'aioredis', 'arcus')


if asyncio:
    from ring.func_asyncio import aiomcache, aioredis
