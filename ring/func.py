"""Collection of cache decorators"""

from ring.func_sync import dict, memcache, redis_py, redis, arcus, disk

try:
    import asyncio
except ImportError:
    asyncio = False

__all__ = ('dict', 'memcache', 'redis_py', 'redis', 'aiomcache', 'aioredis', 'arcus', 'disk')


if asyncio:
    from ring.func_asyncio import aiomcache, aioredis
