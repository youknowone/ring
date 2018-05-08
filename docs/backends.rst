Backends
~~~~~~~~

*Ring* has built-in supports for common cache storages:
  - :func:`ring.dict`: Basic python :class:`dict` based cache.
  - :func:`ring.memcache`: Memcached_
  - :func:`ring.redis`: Redis_
  - :func:`ring.diskcache`: diskcache_
  - :func:`ring.aiodict` :func:`ring.aiomcache` :func:`ring.aioredis` for
    asyncio

Creating a new backend is also quick & easy.

Normal Backends
---------------
.. automodule:: ring.func_sync

.. autofunction:: ring.func_sync.dict
.. autofunction:: ring.func_sync.memcache
.. autofunction:: ring.func_sync.redis
.. autofunction:: ring.func_sync.disk

asyncio Backends
----------------

.. automodule:: ring.func_asyncio

.. autofunction:: ring.func_asyncio.dict
.. autodata:: ring.func_asyncio.aiodict
.. autofunction:: ring.func_asyncio.aiomcache
.. autofunction:: ring.func_asyncio.aioredis


