Why Ring?
=========

Cache is a popular concept widely spread on the broad range of computer
science. But cache interface is not well-developed yet. **Ring** is one of
the solutions for humans. Its approach is close integration with a
programming language.

.. toctree::
    why


Common problems of cache
------------------------

:note: Skip this section if you are familiar with cache and decorator patterns
       for cache in Python world.


The straightforward approach to storage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Traditionally we considered cache as a storage. In that sense, calling useful
``actual_function()`` with an argument for the cached result of
``cached_function()`` looks like next series of works:

.. code-block:: python

    # psuedo code for rough flow
    key = create_key()
    if storage.has(key):
        result = storage.get(key)
    else:
        result = cached_function()
        storage.set(key, result)
    actual_function(result)

What's the problem? We are interested in ``cached_function()`` and
``actual_function()`` instead of ``storage``. But the code is full of storage
operations.


Decorated cache function
~~~~~~~~~~~~~~~~~~~~~~~~

Lots of cache libraries working with immutable functions share the similar
solution. Here is a :func:`functools.lru_cache` example:

.. code-block:: python

    from functools import lru_cache

    @lru_cache(maxsize=32)
    def cached_function():
        ...

    result = cached_function()
    actual_function(result)

This code is a lot more readable. Now the last 2 lines of code show what the
code does. Note that this code even includes the definition of
``cached_function()`` which was not included in the prior code.

If the programming world was built on immutable functions, this is perfect;
But actually not. I really love :func:`functools.lru_cache` but couldn't use
it for most of the cases.

In the real world, lots of functions are not pure function - but still, need
to be cached. Since this also is one of the common problems, there are
solutions too. Let's see Django's view cache which helps to reuse web page for
specific seconds.

.. code-block:: python

    from django.views.decorators.cache import cache_page

    @cache_page(60 * 15)
    def cached_page(request):
        ...

It means the view is cached and the cached data is valid for 15 minutes. In
this case, ``actual_function()`` is inside of the Django. The actual function
will generate HTTP response based on the ``cached_page``. It is good enough
when cache expiration is not a real-time requirement.


Manual expiration
~~~~~~~~~~~~~~~~~

Unfortunately, websites are often real-time. Suppose it was a list of customer
service articles. New articles must be shown up in short time. This is how
`Django`_ handle it with `The per-view cache
<https://docs.djangoproject.com/en/2.0/topics/cache/#the-per-view-cache>`_.

.. code-block:: python

    request = Request(...)  # fake request to create key
    key = get_cache_key(request)
    cache.delete(key)  # expire

:func:`get_cache_key <django.utils.cache.get_cache_key>` and
:data:`cache <django.core.cache.cache>` are global names from Django framework
to control cache. We started from a neat per-view cache decorator - but now it
turns into a storage approach which we demonstrated at first section.

You can control them in a consistent level with **Ring**.

:see: :ref:`lifecycle` section for details.
:see: :func:`ring.django.cache_page` which exactly solved the problem.


Fixed strategy
~~~~~~~~~~~~~~

Sometimes we need more complicated strategy than normal. Suppose we have very
heavy and critical layer. We don't want to lose cache. It must be updated in
every 60 seconds, but without losing the cached version even if it wasn't
updated - or even during it is being updated. With common solutions, we needed
to drop the provided feature but to implement a new one.

You can replace semantics of **Ring** commands and storage behaviors.

:see: :ref:`strategy` section for details.


Hidden backend
~~~~~~~~~~~~~~

You might find another glitch. Their backends are concealed. Memory is ok.
There are fewer reasons to uncover data from it. For services, the common cache
backends are storages and database. Working high-level APIs are good. But we
need to access the storages out of the original product, or even out of the
Python world.

*Ring* has a transparent interface for backends. Moving between high-level
:class:`ring.ring_base.Ring` and low-level storage interfaces is
straightforward and smooth.

:see: :ref:`transparency` section for details.


Data encoding
~~~~~~~~~~~~~

Another issue is Python-specific. Python objects are full of Python metadata
which are not a simple sequence of bytes. Then how do we easily handle them
through cache? The common answer is standard library :mod:`pickle`. Most of
Python objects can be dumped to and loaded from binary with it. This feature
is beloved for a long time in the history of pickle. `python-memcached`_
is a great example.

.. code-block:: python

    class A(object):
        """Custom object with lots of features and data"""
        ...

    client = memcache.Client(...)

    original_data = A()
    client.set(key, data)
    loaded_data = client.get(key)

    assert isinstance(loaded_data, A)  # True
    assert original_data == loaded_data  # mostly True


What's the problem? We don't have any choice. :mod:`pickle` is an amazing idea
but not perfect. In these days, huge giant objects from complex libraries are
roaming over the Python world. Some of them are not pickled well and these will
not be decreased in future because they are modern Python's killer apps.
By environments, to pickle or not to pickle, programmers controlled them over
time.

*Ring* has a configurable data-coding layer. Users can replace it by functions,
by their needs and by injecting code.

:see: :ref:`datacoding` section for details.


.. _lifecycle:

Ring controls cache life-cycle with sub-functions
-------------------------------------------------

The basic usage is similar to :func:`functools.lru_cache` or `Django per-view
cache`.

.. code-block:: python

    import ring

    @ring.dict({})
    def cached_function():
        ...

    result = cached_function()
    actual_function(result)


Extra operations are supported as below:

.. code-block:: python

    cached_function.update()  # force update
    cached_function.delete()  # expire
    cached_function.execute()  # this will not generate cache
    cached_function.get()  # get value only when cache exists


**Ring** provides a common auto-cache approach by default but not only that.
Extra controllers provide full functions for cache policy and storages.

:see: :doc:`control` for details.


Function parameters are also supported in an expected manner:

.. code-block:: python

    @ring.dict({})
    def cached_function(a, b, c):
        ...

    cached_function(10, 20, 30)  # normal call
    cached_function.delete(10, 20, 30)  # delete call


.. _transparency:

Ring approaches backend transparent way
---------------------------------------

High-level interface providers like **Ring** cannot expose full features of
the backends. Various storages have various features by their design. **Ring**
covers common features but does not cover others. :class:`ring.func_base.Ring`
objects serve data extractors instead.

.. code-block:: python

    client = memcache.Client(...)

    @ring.memcache(client)
    def f(a):
        ...

    cache_key = f.key(10)  # cache key for 10
    assert f.storage.backend is client
    encoded_data = f.storage.backend.get(cache_key)  # get from memcache client
    actual_data = f.decode(encoded_data)  # decode

:see: :doc:`control` for details.


.. _datacoding:

Ring provides a configurable data-coding layer
----------------------------------------------

`python-memcached` supports :mod:`pickle` by default but `pylibmc` doesn't.
By adding ``coder='pickle'``, next code will be cached through pickle even
with `pylibmc`. Of course for other backends too.


.. code-block:: python

    client = pylibmc.Client(...)

    @ring.memcache(client, coder='pickle')
    def f(a):
        ...


:see: :doc:`coder` for more informations.

:note: Looks verbose? :func:`functools.partial` is your friend. Try
       ``my_cache = functools.partial(ring.memcache, client, coder='pickle')``.


.. _strategy:

Ring comes with configurable commands and storage actions
---------------------------------------------------------


:see: :class:`ring.func_base.BaseStorage`
:see: :class:`ring.func_sync.CacheUserInterface`
:see: :class:`ring.func_asyncio.CacheUserInterface`

.. _python-memcached: https://pypi.org/project/python-memcached/
.. _Django: https://www.djangoproject.com/
