""":mod:`ring.func` --- Factory functions.
==========================================

Ring object factory functions are aggregated in this module.
"""

from .func_sync import dict, memcache, redis_py, redis, disk

try:
    import asyncio
except ImportError:
    asyncio = False

if asyncio:
    from .func_asyncio import aiodict, aiomcache, aioredis
else:
    aiodict = None
    aiomcache = None
    aioredis = None

__all__ = (
    'dict', 'memcache', 'redis_py', 'redis', 'disk',
    'aiodict', 'aiomcache', 'aioredis')
