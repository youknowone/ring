Factory functions
=================

In this document, you will learn:

  #. About pre-defined factories included in **Ring**.
  #. About storage backends.
  #. About Django extension.


Built-in factory functions and backends
---------------------------------------

**Factory function** means the end user interface of **Ring**, which usually
looks like ``@ring.dict``, ``@ring.memcache``, ``@ring.django``, etc.

Technically the factory functions are not associated with each backend as
bijection, but the built-in functions are mostly matching to the backends.
So practically each factory function part of this document is including
backend descriptions.

**Ring** includes support for common cache storages:

 - :func:`ring.dict`
 - :func:`ring.memcache`
 - :func:`ring.redis`
 - :func:`ring.shelve`
 - :func:`ring.disk`

Which are shortcuts of concrete implementations and tools below:

.. autosummary::
    ring.func.sync.dict
    ring.func.sync.memcache
    ring.func.sync.redis_py
    ring.func.sync.shelve
    ring.func.sync.diskcache
    ring.func.asyncio.dict
    ring.func.asyncio.aiomcache
    ring.func.asyncio.aioredis
    ring.func.asyncio.create_factory_from
    ring.func.asyncio.create_asyncio_factory_proxy


:see: :mod:`ring.func` for built-in backends.


Django extension
----------------

Though **Django** itself is not a storage, it has its own cache API.
**Ring** has a factory function for high-level interface `cache_page` and
the other one `cache` for the low-level interface.

.. autosummary::
    ring.django.cache_page
    ring.django.cache


:see: :mod:`ring.django` for extension.


Common factory parameters
-------------------------

:see: :func:`ring.func.base.factory` for generic factory definition.


.. _factory.shortcut:

Creating factory shortcuts
--------------------------

Usually, each project has common patterns of programming including common cache
pattern. Repeatedly passing common arguments must be boring. Python already
has an answer - use :func:`functools.partial` to create shortcuts.

.. code-block:: python

    import functools
    import ring
    import pymemcache.client

    client = pymemcache.client.Client(('127.0.0.1', 11211))

    # Verbose calling
    @ring.memcache(client, coder='pickle', user_interface=DoubleCacheUserInterface)
    def f1():
        ...

    # Shortcut
    mem_ring = functools.partial(
        ring.memcache, client, coder='pickle',
        user_interface=DoubleCacheUserInterface)

    @mem_ring()
    def f2():
        ...


The decorators of `f1` and `f2` work same.


Custom factory
--------------

:see: :doc:`extend`

