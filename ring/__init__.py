""":mod:`ring` - Top-level interfaces for end users
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Common ring decorators are aliased in this level as shurtcuts.

"""
import ring.coder  # noqa
from ring.func import (
    dict, memcache, redis, disk,
    aiodict, aiomcache, aioredis)
from ring.django import django, django_default


__all__ = (
    'dict', 'memcache', 'redis', 'disk',
    'aiodict', 'aiomcache', 'aioredis',
    'django', 'django_default')
