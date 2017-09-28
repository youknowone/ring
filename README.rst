Ring - The ultimate cache interface.
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. image:: https://travis-ci.org/youknowone/ring.svg?branch=master
    :target: https://travis-ci.org/youknowone/ring

asyncio support!

Take an explicit but fully automated cache.
Ring decorators convert your functions to cached version of them, with extra control methods.


Function cache
--------------

.. code:: python

    import ring
    import memcache
    import requests

    mc = memcache.Client(['127.0.0.1:11211'])

    # working for mc, expire in 60sec
    @ring.func.memcache(mc, time=60)
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
        @ring.func.redis(rc, coder='json')
        def data(self):
            return self.copy()

        # parameters are also ok!
        @ring.func.redis(rc, coder='json')
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
    assert user_data == user2.data()
