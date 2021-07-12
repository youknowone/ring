""":mod:`ring` - Top-level interfaces for end users.
====================================================

Common ring decorators are aliased in this level as shortcuts.
"""
import ring.coder  # noqa
from ring.__version__ import __version__  # noqa
from ring.func import (
    lru, dict, shelve, disk, memcache, redis, redis_hash)
try:
    import asyncio
    from ring.func.asyncio import aiomcache, aioredis, aioredis_hash
except (ImportError, RuntimeError):
    pass
else:
    del asyncio
try:
    import ring.django  # noqa
except ImportError:  # pragma: no cover
    pass


__all__ = (
    'lru', 'dict', 'shelve', 'memcache', 'redis', 'redis_hash', 'disk',
    'aiomcache', 'aioredis', 'aioredis_hash')
