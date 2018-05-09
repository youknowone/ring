Factory functions
~~~~~~~~~~~~~~~~~

In this document, you will learn:

  #. About :class:`ring.func_base.Ring` factory.
  #. About built-in factories.
  #. About storage backends.
  #. About django extension.

Built-in factory functions and backends
---------------------------------------

**Factory function** means the end user interface of **Ring**, which usually
look like ``@ring.dict``, ``@ring.memcache``, ``@ring.django``, etc.

Technically the factory functions are not associated to each backends as
bijection, but the built-in functions are mostly matching to the backends.
So practically each factory function part of this document is including
backend descriptions.

**Ring** has built-in supports for common cache storages:

.. autosummary::
    ring.dict
    ring.memcache
    ring.redis
    ring.disk
    ring.dict
    ring.aiomcache
    ring.aioredis


:see: :mod:`ring.func` for built-in backends.


Django extension
----------------

Creating a new factory function is also quick & easy.

Though **Django** is not a storage, but it has its own low-level cache api.
**Ring** has a factory function for Django as a cache backend:

.. autosummary::
    ring.django
    ring.django_default


:see: :mod:`ring.django` for extension.


Custom factory
--------------
(TBD)

