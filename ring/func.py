"""Collection of cache decorators"""

from ring.func_sync import dict, memcache, redis_py, redis, disk
from ring.django import django, django_default

try:
    import asyncio
except ImportError:
    asyncio = False

if asyncio:
    from ring.func_asyncio import aiodict, aiomcache, aioredis
else:
    aiodict = None
    aiomcache = None
    aioredis = None

__all__ = (
    'dict', 'memcache', 'redis_py', 'redis', 'disk',
    'aiodict', 'aiomcache', 'aioredis',
    'django', 'django_default')
