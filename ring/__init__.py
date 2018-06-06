""":mod:`ring` - Top-level interfaces for end users.
====================================================

Common ring decorators are aliased in this level as shortcuts.

"""
import ring.coder  # noqa
from ring.func import (
    dict, memcache, redis, disk,
    aiodict, aiomcache, aioredis)
import ring.django  # noqa


__all__ = (
    'dict', 'memcache', 'redis', 'disk',
    'aiodict', 'aiomcache', 'aioredis')
