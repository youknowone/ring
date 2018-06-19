""":mod:`ring.func` --- Factory functions.
==========================================

Ring object factory functions are aggregated in this module.
"""

from .func_sync import dict, shelve, memcache, redis_py, redis, disk
from . import func_sync

try:
    import asyncio
except ImportError:
    asyncio = False

if asyncio:
    from .func_asyncio import aiomcache, aioredis
    from . import func_asyncio
else:
    aiodict = None
    aiomcache = None
    aioredis = None

__all__ = (
    'dict', 'shelve', 'memcache', 'redis_py', 'redis', 'disk',
    'aiomcache', 'aioredis')


if asyncio:
    dict = func_asyncio.create_factory_proxy(
        (dict, func_asyncio.dict),
        allow_asyncio=True)
    shelve = func_asyncio.create_factory_proxy(
        (shelve, func_asyncio.create_from(func_sync.ShelveStorage)),
        allow_asyncio=False)
    disk = func_asyncio.create_factory_proxy(
        (disk, func_asyncio.create_from(func_sync.DiskStorage)),
        allow_asyncio=False)
