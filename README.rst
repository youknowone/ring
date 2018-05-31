Ring
====

.. image:: https://travis-ci.org/youknowone/ring.svg?branch=master
    :target: https://travis-ci.org/youknowone/ring
.. image:: https://codecov.io/gh/youknowone/ring/graph/badge.svg
    :target: https://codecov.io/gh/youknowone/ring

Let's concentrate on code, not on storages.

Ring shows a way to control cache in point of view of code - not about storages.
Ring's decorator is convenient but also keeps fluency for general scenarios.

asyncio support!

Take advantage of perfectly explicit and fully automated cache interface.
Ring decorators convert your functions to cached version of them, with extra
control methods.


Documentation
-------------

Full documentation with examples and references:
`<http://ring-cache.readthedocs.io/>`_

- Function/method support.
- asyncio support.
- Django support.
- Bulk access support.


Function cache
--------------

.. code:: python

    import ring
    import memcache
    import requests

    mc = memcache.Client(['127.0.0.1:11211'])

    # working for mc, expire in 60sec
    @ring.memcache(mc, time=60)
    def get_url(url):
        return requests.get(url).content

    # normal way - it is cached
    data = get_url('http://example.com')

It is a normal smart cache flow.

But ring is different when you want to explicitly control it.


.. code:: python

    # delete the cache
    get_url.delete('http://example.com')
    # get cached data or None
    data_or_none = get_url.get('http://example.com')

    # get internal cache key
    key = get_url.key('http://example.com')
    # and access directly to the backend
    direct_data = mc.get(key)


Method cache
------------

.. code:: python

    import ring
    import redis

    rc = redis.StrictRedis()

    class User(dict):
        def __ring_key__(self):
            return self['id']

        # working for rc, no expiration
        # using json coder for non-bytes cache data
        @ring.redis(rc, coder='json')
        def data(self):
            return self.copy()

        # parameters are also ok!
        @ring.redis(rc, coder='json')
        def child(self, child_id):
            return {'user_id': self['id'], 'child_id': child_id}

    user = User(id=42, name='Ring')

    # create and get cache
    user_data = user.data()  # cached
    user['name'] = 'Ding'
    # still cached
    cached_data = user.data()
    assert user_data == cached_data
    # refresh
    updated_data = user.data.update()
    assert user_data != updated_data

    # id is the cache key so...
    user2 = User(id=42)
    # still hitting the same cache
    assert updated_data == user2.data()


Installation
------------

PyPI is the recommended way.

.. sourcecode:: shell

    $ pip install ring

To browse versions and tarballs, visit:
    `<https://pypi.python.org/pypi/ring/>`_


To use memcached or redis, don't forget to install related libraries.
For example: python-memcached, python3-memcached, pylibmc, redis-py, Django etc

It may require to install and run related services on your system too.
Look for `memcached` and `redis` for your system.


Contributors
------------

See contributors list on:
    `<https://github.com/youknowone/ring/graphs/contributors>`_

