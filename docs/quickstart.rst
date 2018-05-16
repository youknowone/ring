Quickstart
==========

To start, remember the philosophy of **Ring** is a human-friendly high-level
interface *with* transparent and concrete low-level access. You probably be
able to access most of the level of **Ring** you want.


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

If you are new to **Ring** and cache, :func:`ring.dict` doesn't
require any dependency. Let's start with it. Moving from dict to another
backend is easy.


First example
-------------

Let's start from a simple example: function cache with bytes data.

.. code-block:: python

    import ring
    import requests

    # save in a dict, expire in 60 seconds.
    @ring.dict({}, time=60)
    def get_url(url):
        return requests.get(url).content

    # default access - it is cached
    data = get_url('http://example.com')

This flow is what you see in common *smart* cache decorators.


The core feature of **Ring** is explicit controllers.

.. code-block:: python

    # delete the cache
    get_url.delete('http://example.com')
    # get cached data or None
    data_or_none = get_url.get('http://example.com')

    # get internal cache key
    key = get_url.key('http://example.com')
    # and access directly to the backend
    encoded_data = get_url.storage.get(key)
    cached_data = get_url.decode(encoded_data)


Ring will have full control for any layer of caching.

:see: :doc:`control` for sub-functions details.
:see: :doc:`why` if this document doesn't explain what **Ring** does.


method, classmethod, staticmethod, property
-------------------------------------------

**Ring** is adaptable for any kind of methods for Python class.

(TBD)


Choosing backend
----------------

Let's consider using actual cache storage instead :class:`dict`.

**Ring** includes common cache storage supports. `Memcached` is one of the
popular cache storage. `Memcached` itself is out of the Python world. You must
install and run it to let your python code connects there. Because `Memcached`
is very popular, it is well-packaged in most of the platforms. Check how to
install it on your platform.

:note: ``apt install memcached`` for Debian/Ubuntu. ``yum install memcached``
       for CentOS/RHEL ``brew install memcache`` for macOS with Homebrew_.

Once you installed it, do not forget to start it.

In **Ring**, you can choose any compatible memcached package. If you are new
to memcached, let's try pymemcache_ to install it easily.

.. sourcecode:: shell

    $ pip install pymemcache


Now you are ready to edit the ``get_url`` to use Memcached.

.. code-block:: python

    import ring
    import requests
    import pymemcache   #1 import pymemcache

    client = pymemcache.Client((127.0.0.1, 11211))  #2 create a client

    # save to memcache client, expire in 60 seconds.
    @ring.memcache(client, time=60)  #3 dict -> memcache
    def get_url(url):
        return requests.get(url).content

    # default access - it is cached
    data = get_url('http://example.com')


Try and compare what's changed from :func:`ring.dict` version.

There are many more included factories for various backends.

:see: :doc:`factory` about more factories and backends.

.. _Homebrew: https://brew.sh/
.. _pymemcache: https://pypi.org/project/pymemcache/


:mod:`asyncio` support
~~~~~~~~~~~~~~~~~~~~~~

**Ring** supports :mod:`asyncio` with a few factories which also are included.

:note: the sync version factories are not compatible with :mod:`asyncio`.

:see: :doc:`factory` and search for `asyncio` to find fit factories.


Complex data
------------

:see: :doc:`coder` about more backends.


Low-level access
----------------


Further documents
-----------------

:see: :doc:`why`
:see: :doc:`control`
:see: :doc:`ring` --- the full reference of **Ring**
