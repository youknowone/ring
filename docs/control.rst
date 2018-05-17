Attributes of Ring object
=========================

A Ring-decorated function is a Ring object. Ring objects have common attributes
which give elaborate controlling. Note that `object` in `Ring object` doesn't
mean Python object. They are a collection of Ring-interface-injected stuff
which share interface described in this document.

Though it is up to factory functions :func:`ring.func_sync.ring_factory`
and :func:`ring.func_asyncio.ring_factory`, they share following features.


Meta controller
---------------

.. function:: run(function_name[, *args, **kwargs])

    Meta sub-function. It calls the given `function_name` named sub-function
    with given parameters ``*args`` and ``**kwargs``.

    :param str function_name: A sub-function name except for `run`

    For example:

    .. code-block:: python

        @ring.dict(...)
        def f(a, b):
            ...

        f.run('execute', 1, 2)  # run execute with argument 1 and 2
        f.execute(1, 2)  # same


Building blocks
---------------

.. data:: storage

    Cache storage where the cached data be saved.

    For most of the included factories, it returns the first argument of the
    **Ring** factories.

    For example:

    .. code-block:: python

        storage = {}

        @ring.dict(storage)
        def f():
            ...

        assert f.storage is storage

    .. code-block:: python

        client = memcache.Client(...)

        @ring.memcache(client)
        def f():
            ...

        assert f.storage is client


.. function:: decode(cache_data)

    Decode cache data to actual data.

    When a coder is passed as ``coder`` argument of a **Ring** factory, this
    function includes ``coder.decode``.

    :note: experimental

    Though **Ring** doesn't have a concrete design of this function yet, the
    assumption expects:

    .. code-block:: python

        @ring...
        def f():
            ...

        r1 = f.get()
        # storage.get may vary by actual storage object
        r2 = f.decode(f.storage.get(f.key()))
        assert r1 == r2


.. function:: encode(raw_data)

    Encode raw actual data to cache data.

    When a coder is passed as ``coder`` argument of a **Ring** factory, this
    function includes ``coder.encode``.

    :note: experimental

    Though **Ring** doesn't have a concrete design of this function yet, the
    assumption expects 3 ways below working same.

    .. code-block:: python

        @ring...
        def f():
            ...

        # way #1
        f.update()
        # way #2
        result = f.execute()
        f.set(f.encode(result))
        # way #3
        # storage.set may vary by actual storage object
        f.storage.set(f.key(), f.encode(result))


Cache behavior controller
-------------------------

Note that behavior controllers are not fixed as the following meaning. This
section is written to describe what **Ring** and its users expect for each
function, not to define what these functions actually do.

To change behavior, inherit :class:`ring.sync.CacheInterface` or
:class:`ring.asyncio.CacheInterface` then passes it to ``cache_interface``
parameter of **Ring** factories.


.. function:: get_or_update([*args, **kwargs])

    Try to get the cached data with the given arguments; otherwise, execute the
    function and update cache.

    This is the default behavior of most of Ring objects.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Try to get cached data by the key.
    #. If cache data exists, return it.
    #. Otherwise, execute the original function to create a result.
    #. Set the result as the value of created cache key.


.. function:: execute([*args, **kwargs])

    Execute the original function with given arguments.

    This sub-function is exactly the same as calling the original function.


.. function:: key([*args, **kwargs])

    Create a cache key with given arguments.


.. function:: get([*args, **kwargs])

    Try to get the cache data; otherwise, execute the function and update cache.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Try to get cached data by the key.
    #. If cache data exists, return it.
    #. Otherwise, return ``miss_value`` which normally is :data:`None`.


.. function:: update([*args, **kwargs])

    Update cache data for the given arguments.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Execute the original function to create a result.
    #. Set the result as cache data of created cache key.


.. function:: set(value, [*args, **kwargs])

    Set value as cache data for the given arguments.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Set the value as cache data of created cache key.


.. function:: delete([*args, **kwargs])

    Delete cache data for the given arguments.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Delete the value of created cache key.


.. function:: touch([*args, **kwargs])

    Touch cache data of the given arguments. `Touch` means extending expiration
    time.

    :note: Unlike other sub-functions, this feature may not be supported by
           backends.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Touch the value of created cache key.
