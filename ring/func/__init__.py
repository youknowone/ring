""":mod:`ring.func` --- Factory functions.
==========================================

Ring object factory functions are aggregated in this module.
"""
from __future__ import absolute_import
from ring.func import sync

try:
    import asyncio as asyncio_mod
except ImportError:
    asyncio_mod = False
else:
    from . import asyncio


__all__ = (
    'dict', 'memcache', 'redis', 'shelve', 'disk')


if asyncio_mod:
    dict = asyncio.create_asyncio_factory_proxy(
        (sync.dict, asyncio.dict),
        support_asyncio=True)
    shelve = asyncio.create_asyncio_factory_proxy(
        (sync.shelve, asyncio.create_factory_from(sync.ShelveStorage)),
        support_asyncio=False)
    disk = asyncio.create_asyncio_factory_proxy(
        (sync.diskcache, asyncio.create_factory_from(sync.DiskCacheStorage)),
        support_asyncio=False)
    memcache = asyncio.create_asyncio_factory_proxy(
        (sync.memcache, asyncio.aiomcache),
        support_asyncio=True)
    redis = asyncio.create_asyncio_factory_proxy(
        (sync.redis_py, asyncio.aioredis),
        support_asyncio=True)
else:
    from .sync import dict, shelve, diskcache as disk, memcache, redis_py as redis
