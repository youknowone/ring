:mod:`ring`
===========

.. toctree::
   :maxdepth: 2
   :caption: User interfaces

   ring/func
   ring/func_sync
   ring/func_asyncio
   ring/func_base
   ring/coder
   ring/django

.. automodule:: ring

    .. function:: dict(...)

        Proxy to select synchronous or :mod:`asyncio` versions of **Ring**
        factory.

        :see: :func:`ring.func.sync.dict` for synchronous version.
        :note: :mod:`asyncio` version is based on synchronous version. It is
            composed using :func:`ring.func.asyncio.convert_storage`.

    .. function:: memcache(...)

        Proxy to select synchronous or :mod:`asyncio` versions of **Ring**
        factory.

        :see: :func:`ring.func.sync.memcache` for synchronous version.
        :see: :func:`ring.func.asyncio.aiomcache` for :mod:`asyncio` version.

    .. function:: redis(...)

        Proxy to select synchronous or :mod:`asyncio` versions of **Ring**
        factory.

        :see: :func:`ring.func.sync.redis_py` for synchronous version.
        :see: :func:`ring.func.asyncio.aioredis` for :mod:`asyncio` version.

    .. function:: shelve(...)

        Proxy to select synchronous or :mod:`asyncio` versions of **Ring**
        factory.

        :see: :func:`ring.func.sync.shelve` for synchronous version.
        :note: :mod:`asyncio` version is based on synchronous version. It is
            composed using
            :func:`ring.func.asyncio.create_asyncio_factory_proxy`.
        :warning: The backend storage of this factory doesn't support
            :mod:`asyncio`. To enable asyncio support at your own risk,
            pass `force_asyncio=True` as a keyword parameter.
            parameter.

    .. function:: disk(...)

        Proxy to select synchronous or :mod:`asyncio` versions of **Ring**
        factory.

        :see: :func:`ring.func.sync.diskcache` for synchronous version.
        :note: :mod:`asyncio` version is based on synchronous version. It is
            composed using
            :func:`ring.func.asyncio.create_asyncio_factory_proxy`.
        :warning: The backend storage of this factory doesn't support
            :mod:`asyncio`. To enable asyncio support at your own risk,
            pass `force_asyncio=True` as a keyword parameter.
            parameter.

    .. autofunction:: ring.aiomcache
    .. autofunction:: ring.aioredis
