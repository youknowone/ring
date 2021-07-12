""":mod:`ring.func` --- Factory functions.
==========================================

Ring object factory functions are aggregated in this module.
"""
from __future__ import absolute_import
from ring.func import sync

try:
    import asyncio as _has_asyncio
except (ImportError, RuntimeError):
    _has_asyncio = False
else:
    try:
        from ring.func import asyncio
    except RuntimeError:
        _has_asyncio = False


__all__ = (
    'lru', 'dict', 'memcache', 'redis', 'redis_hash', 'shelve', 'disk')


if _has_asyncio:
    lru = asyncio.create_asyncio_factory_proxy(
        (sync.lru, asyncio.create_factory_from(sync.lru, sync.LruStorage)),
        support_asyncio=False)
    dict = asyncio.create_asyncio_factory_proxy(
        (sync.dict, asyncio.dict),
        support_asyncio=True)
    shelve = asyncio.create_asyncio_factory_proxy(
        (sync.shelve, asyncio.create_factory_from(sync.shelve, sync.ShelveStorage)),
        support_asyncio=False)
    disk = asyncio.create_asyncio_factory_proxy(
        (sync.diskcache, asyncio.create_factory_from(sync.diskcache, sync.DiskCacheStorage)),
        support_asyncio=False)
    memcache = asyncio.create_asyncio_factory_proxy(
        (sync.memcache, asyncio.aiomcache),
        support_asyncio=True)
    redis = asyncio.create_asyncio_factory_proxy(
        (sync.redis_py, asyncio.aioredis),
        support_asyncio=True)
    redis_hash = asyncio.create_asyncio_factory_proxy(
        (sync.redis_py_hash, asyncio.aioredis_hash),
        support_asyncio=True)
else:
    from .sync import (
        lru, dict, shelve, diskcache as disk, memcache,
        redis_py as redis, redis_py_hash as redis_hash)
