Quickstart
==========

To start, remember the philosophy of **Ring** is a human-friendly high-level
interface *with* transparent and concrete low-level access. You probably be
able to access most of the levels of **Ring** you want.


Installation
------------

PyPI is the recommended way.

.. sourcecode:: shell

    $ pip install ring

To browse versions and tarballs, visit:
    `<https://pypi.python.org/pypi/ring/>`_


Though **Ring** includes support for many backends, their packages are not
included in ring installation due to the following issues:

  #. Ring supports many backends but users don't use all of them.
  #. Backends packages not only cost storages and time but also require some
     non-Python packages to be installed, which cannot be automated by pip.
  #. Installing some of them is not easy on some platforms.

Check each backend you use and manually add related packages to `setup.py`
or `requirements.txt`.

If you are new to **Ring** and cache, let's start with :func:`ring.lru`.
It doesn't require any dependency. Changing lru to another backend is simple
for later.

.. note::

    If you are new to LRU cache, check
    `<https://en.wikipedia.org/wiki/Cache_replacement_policies#Least_recently_used_(LRU)>`_
    for details.


First example
-------------

Let's start with a simple example: function cache with bytes data.

.. code-block:: python

    import ring
    import requests

    # save in a new lru storage
    @ring.lru()
    def get_url(url):
        return requests.get(url).content

    # default access - it is cached
    data = get_url('http://example.com')

This flow is what you see in common *smart* cache decorators. Actually, this is
very similar to :func:`functools.lru_cache` in Python standard library.

The differences start here.
The core feature of **Ring** is explicit controllers.

.. code-block:: python

    # delete the cache
    get_url.delete('http://example.com')
    # get cached data or None
    data_or_none = get_url.get('http://example.com')

    # get internal cache key
    key = get_url.key('http://example.com')
    # and access directly to the backend
    encoded_data = get_url.storage.backend.get(key)
    cached_data = get_url.decode(encoded_data)


Ring will have full control for any layer of caching. Which doesn't exist
in :func:`functools.lru_cache`

:see: :doc:`control` for sub-functions details.
:see: :doc:`why` if this document doesn't explain what **Ring** does.


method, classmethod, staticmethod, property
-------------------------------------------

**Ring** is adaptable for any kind of methods for Python class.

.. code-block:: python

    import ring
    import requests

    class Page(object):

        base_content = '<html></html>'

        def __init__(self, url):
            self.url = url

        def __ring_key__(self):
            return 'page=' + self.url

        @ring.lru()
        def content(self):
            return requests.get(self.url).content

        @ring.lru()
        @classmethod
        def class_content(cls):
            return cls.base_content

        @ring.lru()
        @staticmethod
        def example_dot_com():
            return requests.get('http://example.com').content

        @ring.lru()
        @property
        def url_property(self):
            return self.url_property


    Page.example_dot_com()  # as expected
    assert Page.example_dot_com.key().endswith('Page.example_dot_com')  # key with function-name

    Page.class_content()  # as expected
    # key with function-name + class name
    assert Page.class_content.key().endswith('Page.class_content:Page')

    p = Page('http://example.com')
    p.content()  # as expected
    # key with class name + function name + __ring_key__
    assert p.content.key().endswith('Page.content:page=http://example.com')

    assert p.url_property == p.url


:see: :doc:`factory` for details.


Choosing backend
----------------

Let's consider using external cache storage instead of :class:`lru`.

**Ring** includes common cache storage supports. `Memcached` is one of the
popular cache storage. `Memcached` itself is out of the Python world. You must
install and run it to let your python code connects there. Fortunately,
because `Memcached` is very popular, it is well-packaged on most of the
platforms. Check how to install it on your platform.

:note: For example, ``apt install memcached`` for Debian/Ubuntu.
    ``yum install memcached`` for CentOS/RHEL. ``brew install memcache`` for
    macOS with Homebrew_.

Once you installed it, do not forget to start it.

In **Ring**, you can choose any compatible Memcached package. If you are new
to Memcached, let's try pymemcache_ to install it easily.

.. sourcecode:: shell

    $ pip install pymemcache


Now you are ready to edit the ``get_url`` to use Memcached.

.. code-block:: python

    import ring
    import requests
    import pymemcache.client   #1 import pymemcache

    client = pymemcache.client.Client(('127.0.0.1', 11211))  #2 create a client

    # save to memcache client, expire in 60 seconds.
    @ring.memcache(client, expire=60)  #3 lru -> memcache
    def get_url(url):
        return requests.get(url).content

    # default access - it is cached
    data = get_url('http://example.com')


Try and compare what's changed from :func:`ring.lru` version.

There are many more included factories for various backends.

:see: :doc:`factory` about more factories and backends.
:see: :doc:`extend` to create your own factory.

.. _Homebrew: https://brew.sh/
.. _pymemcache: https://pypi.org/project/pymemcache/


:mod:`asyncio` support
~~~~~~~~~~~~~~~~~~~~~~

**Ring** supports :mod:`asyncio` with a few factories which also are included.
They follow similar convention but requiring `await` for IO jobs.

.. code-block:: python

    import ring

    @ring.lru()
    async def f():
        ...

    result = await f()  # using `await` for __call__
    cached_result = await f.get()  # using `await` for get()
    key = f.key()  # NOT using `await` for key()


:note: Non-IO sub-functions doesn't require `await`.
:note: the sync version factories are not compatible with :mod:`asyncio`.

:see: :doc:`factory` and search for `asyncio` to find fit factories.


Structured or complex data
--------------------------

The modern software handles structured data rather than chunks of bytes.
Because the popular cache storages only support raw bytes or string, data
needs to be encoded and decoded. The `coder` parameter in Ring factories
decides the kind of coding.

.. code-block:: python

    import ring
    import json
    import pymemcache.client

    client = pymemcache.client.Client(('127.0.0.1', 11211))

    @ring.memcache(client, expire=60, coder='json')
    def f():
        return {'key': 'data', 'number': 42}


    f()  # create cache data
    loaded = f.get()
    assert isinstance(loaded, dict)
    assert loaded == {'key': 'data', 'number': 42}
    raw_data = f.storage.backend.get(f.key())
    assert isinstance(raw_data, bytes)  # `str` for py2
    assert raw_data == json.dumps({'key': 'data', 'number': 42}).encode('utf-8')


:see: :doc:`coder` about more backends.
:see: :doc:`extend` to create and register your own coders.


Factory parameters
------------------

Ring factories share common parameters to control Ring objects' behavior.

- key_prefix
- coder
- ignorable_keys
- user_inferface
- storage_interface

:see: :doc:`factory` for details.


Low-level access
----------------

Do you wonder how your data is encoded? Which keys are mapped to the
functions? You don't need to be suffered by looking inside of **Ring**.
At this time, let's use :func:`ring.dict` to look into the storage.

.. code-block:: python

    import ring

    dict_storage = {}

    @ring.dict(dict_storage)
    def f():
        ...

    key = f.key()  # retrieving the key
    raw_data = f.storage.backend.get(key)  # getting raw data from storage

    # look into `dict_storage` by yourself to check how it works.


:see: :doc:`control` for more attributes.


Bulk access
-----------

Bulk access API is optionally supported.

.. code-block:: python

    @ring.memcache(...)
    def f(a, b):
        ...

    # getting data for f(1, 2), f(1, 3), f(a=2, b=2)
    data = f.get_many((1, 2), (1, 3), {'a': 2, 'b': 2})


:see: :doc:`control` for more attributes.


Further documents
-----------------

:see: :doc:`why`
:see: :doc:`control`
:see: :doc:`ring` --- the full reference of **Ring**
