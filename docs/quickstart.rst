Quickstart
~~~~~~~~~~

To start, remember the philosophy of **Ring** is human-friendly high-level
interface *with* transparent and concrete low-level access. You probably be
able to access most of the level of **Ring** you want.


Installation
------------

PyPI is the recommended way.

.. sourcecode:: shell

    $ pip install ring

To browse versions and tarballs, visit:
    `<https://pypi.python.org/pypi/ring/>`_


Though **Ring** includes built-in supports for many backends, they are not
included in ring installation due to the following issues:

  #. Ring supports many backends but users don't use all of them.
  #. Backends packages not only cost storages and time, but also require some
     non-Python packages to be installed, which cannot be automated by pip.
  #. Installing some of them is not easy on some platforms.

Check each backend you use and manually add related packages to `setup.py`
or `requirements.txt`.

If you are new to **Ring** and cache, :func:`ring.dict` doesn't
require any dependency. Let's start with it. Moving from dict to another
backend is easy.


First example
-------------

Let's start from simple example: function cache with bytes data.

.. code:: python

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

.. code:: python

    # delete the cache
    get_url.delete('http://example.com')
    # get cached data or None
    data_or_none = get_url.get('http://example.com')

    # get internal cache key
    key = get_url.key('http://example.com')
    # and access directly to the backend
    encoded_data = get_url.storage.get(key)
    cached_data = get_url.decode(encoded_data)


(TBD)

:see: :doc:`why` if this document doesn't explain what **Ring** does.

Choosing backend
----------------

:see: :doc:`factory` about more backends.


Complex data
------------

:see: :doc:`coder` about more backends.


Low-level access
----------------


Further documents
-----------------

:see: :doc:`why`.
:see: :doc:`ring` the full reference of **Ring**
