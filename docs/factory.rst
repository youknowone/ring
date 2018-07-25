Factory functions
=================

In this document, you will learn:

  #. About pre-defined factories included in **Ring**.
  #. About storage backends.
  #. About target functions and descriptors.
  #. About Django extension.
  #. About common tips.


Built-in factory functions and backends
---------------------------------------

**Factory function** means the end user interface of **Ring**, which usually
looks like ``@ring.dict``, ``@ring.memcache``, ``@ring.django``, etc. These
factory functions create concrete ring decorators by arguments.

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


Target functions and descriptors
--------------------------------

Ring decorators can be adapted to any kind of methods and descriptors.

:note: **Ring** decorator must be placed at the top-most position. The
    descriptors themselves are not functions. **Ring** needs to be on the top
    to look into them to run descriptors in the proper way.


.. code-block:: python

    class A(object):

        v = None

        def __ring_key__(self):
            '''convert self value typed 'A' to ring key component'''
            return v

        @ring.dict({})
        def method(self):
            '''method support'''
            ...

        @ring.dict({})
        @classmethod
        def cmethod(self):
            '''classmethod support'''
            ...

        @ring.dict({})
        @staticmethod
        def smethod(self):
            '''staticmethod support'''
            ...

        @ring.dict({})
        @property
        def property(self):
            '''property support'''
            ...


Any custom descriptors following common conventions will be supported:

- The decorator has the original function as a getter attribute. For example,
    `classmethod` has `__func__` attribute. `property` has `fget` attribute.
- Any descriptor returning a callable is a method descriptor; Otherwise
    property.
- When a descriptor is a method descriptor, it must be a static, class,
    object or hybrid method for any kind of parameter input.
  - A static method descriptor returns a non-method function or method which
    doesn't take an object of the type or the class type as the first argument.
  - A class method descriptor returns a method function which takes the class
    type as the first argument.
  - An object method descriptor returns a method function which takes an object
    of the type.
  - A hybrid method can be a combination of one of the static, class or object
    method by each caller type of object or type class. The hybrid method
    should keep consistency for the same type of the caller.
- When a descriptor is a property descriptor, it must return non-callable
    object. Note that normal python function returning a callable makes sense
    but not much about **Ring**. We don't save python functions in storages.
- For advanced descriptor control, see :func:`wirerope.wire.descriptor_bind`.


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

