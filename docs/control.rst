Attributes of Ring object
=========================

A Ring-decorated function is a Ring object. Ring objects have common attributes
which give elaborate controlling. Note that `object` in `Ring object` doesn't
mean Python object. They are a collection of Ring-interface-injected stuff
which shares interface described in this document.


Meta controller
---------------

.. function:: run(function_name[, *args, **kwargs])

    Meta sub-function. It calls the given `function_name` named sub-function
    with given parameters ``*args`` and ``**kwargs``.

    :param str function_name: A sub-function name except for `run`

    For example:

    .. code-block:: python

        @ring.lru()
        def f(a, b):
            ...

        f.run('execute', 1, 2)  # run execute with argument 1 and 2
        f.execute(1, 2)  # same


Building blocks
---------------

These components are defined in :class:`ring.func.base.RingRope` and shared by
wires.

.. data:: storage

    Cache storage where the cached data be saved.

    This is an instance of BaseStorage of each data. It includes
    `backend` attribute which refers actual storage backend - the first
    argument of the **Ring** factories for most of the included factories.

    For example:

    .. code-block:: python

        storage = {}

        @ring.dict(storage)
        def f():
            ...

        assert f.storage.backend is storage

    .. code-block:: python

        client = memcache.Client(...)

        @ring.memcache(client)
        def f():
            ...

        assert f.storage.backend is client


.. function:: decode(cache_data)

    Decode cache data to actual data.

    When a coder is passed as ``coder`` argument of a **Ring** factory, this
    function includes ``coder.decode``.

    :note: experimental

    Though **Ring** doesn't have a concrete design of this function yet, the
    assumption expects:

    .. code-block:: python

        @ring.dict({})
        def f():
            ...

        f.set('some_value')
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

        @ring.dict({})
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

To change behavior, inherit :class:`ring.sync.CacheUserInterface` or
:class:`ring.asyncio.CacheUserInterface` then passes it to the `user_interface`
parameter of **Ring** factories.


.. function:: key([*args, **kwargs])

    Create and return a cache key with given arguments.


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

    Execute the original function with given arguments and return the result.

    This sub-function is exactly the same as calling the original function.


.. function:: get([*args, **kwargs])

    Try to get the cache data; Otherwise, execute the function and update cache.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Try to get cached data by the key.
    #. If cache data exists, return it.
    #. Otherwise, return `miss_value` which normally is :data:`None`.


.. function:: update([*args, **kwargs])

    Execute the function, update cache data and return the result.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Execute the original function to create a result.
    #. Set the result as cache data of created cache key.
    #. Return the execution result.


.. function:: set(value, [*args, **kwargs])

    Set the given value as cache data for the given arguments.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Set the value as cache data of created cache key.


.. function:: delete([*args, **kwargs])

    Delete cache data for the given arguments.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Delete the value of created cache key.


.. function:: has([*args, **kwargs])

    Check and return existence of cache data for the given arguments.

    :note: Unlike other sub-functions, this feature may not be supported by
           the backends.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Check the value of created cache key exists.
    #. Return the existence.


.. function:: touch([*args, **kwargs])

    Touch cache data of the given arguments. `Touch` means extending expiration
    time.

    :note: Unlike other sub-functions, this feature may not be supported by
           the backends.

    The behavior follows next steps:

    #. Create a cache key with given parameters.
    #. Touch the value of created cache key.


The bulk access controller
--------------------------

The bulk access controller is an optional feature. The backends may or may not
implements the feature.

**args_list** is the common variable-length positional argument. It is a
sequence of arguments of the original function. While **args_list** is a
list of **args**, each **args** is typed as :class:`Union[tuple,dict]`.
Each of them is a complete set of positional-only formed or keyword-only
formed arguments.

When the **args** is positional-only formed, its type
must be always :class:`tuple`. Any other iterable types like `list`
are not allowed. When any keyword-only argument is required, use
keyword-only formed arguments.

When the **args** is keyword-only formed, its type must be always
:class:`dict`. When there is a variable-length positional argument,
pass the values them as a :class:`tuple` of parameters with the
corresponding variable-length positional parameter name.


.. function:: get_or_update_many(*args_list)

    Try to get the cached data with the given arguments list; Otherwise,
    execute the function and update cache.

    The basic idea is:

    #. Try to retrieve existing data as much as possible.
    #. Update missing values.

    :note: The details of this function may vary by the implementation.


.. function:: execute_many(*args_list)

    `Many` version of **execute**.


.. function:: key_many(*args_list)

    `Many` version of **key**.


.. function:: get_many(*args_list)

    `Many` version of **get**.


.. function:: update_many(*args_list)

    `Many` version of **update**.


.. function:: set_many(args_list, value_list)

    `Many` version of **set**.

    :note: This function has a little bit different signature to other
        bulk-access controllers and **set**.


.. function:: has_many(*args_list)

    `Many` version of **has**.


.. function:: delete_many(*args_list)

    `Many` version of **delete**.


.. function:: touch_many(*args_list)

    `Many` version of **touch**.


.. _control.override:

Override behaviors
------------------

Each ring rope can override their own behaviors.

.. function:: ring.key(...)

    Override key composer. Parameters are the same as the original function.

    >>> @ring.dict({})
    >>> def f(a, b):
    ...     return ...
    ...
    >>> assert f.key(1, 2) == '__main__.f:1:2'  # default key
    >>>
    >>> @f.ring.key
    ... def f_key(a, b):
    ...     return 'a{}b{}'.format(a, b)
    ...
    >>> assert f.key(1, 2) == 'a1b2'  # new key


.. function:: ring.encode(value)

    Override data encode function.

    :see: :doc:`coder`

.. function:: ring.decode(data)

    Override data decode function.

    :see: :doc:`coder`
