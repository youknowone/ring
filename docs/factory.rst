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

.. autosummary::
    ring.dict
    ring.memcache
    ring.redis
    ring.disk
    ring.aiodict
    ring.aiomcache
    ring.aioredis


:see: :mod:`ring.func` for built-in backends.


Django extension
----------------

Creating a new factory function is also quick & easy.

Though **Django** itself is not a storage, it has its own low-level cache API.
**Ring** has a factory function for Django as a cache backend:

.. autosummary::
    ring.django
    ring.django_default


:see: :mod:`ring.django` for extension.


Common factory parameters
-------------------------

.. function:: <general_factory_function>(storage_backend, [key_prefix=None,
        expire=None, coder=None, ignorable_keys=None,
        interface=CacheUserInterface, storage_class=StorageClass])

    :note: This is about the general factory description, not a specific
        factory called `general_factory_function`.

    :param Optional[str] key_prefix: Specify cache key prefix. Key prefix will
        be automatically created when :data:`None` is passed.
    :param Optional[float] expire: Set duration of seconds to expire the data.
        Usually the default behavior depends on the backend.
    :param Union[str,ring.coder.Coder] coder: Registered coder name or coder
        object. See :doc:`coder` for details.
    :param List[str] ignorable_keys: (unstable) Parameter names not to use to
        create cache key.
    :param Union[ring.func_sync.CacheUserInterface,ring.func_asyncio.CacheUserInterface] interface:
        Injective implementation of sub-functions.
    :param ring.func_base.BaseStorage storage_class:
        Injective implementation of storage.


:see: :func:`ring.func_base.factory` for generic factory definition.


Creating factory shortcuts
--------------------------

Usually each project has common patterns of programming including common cache
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

