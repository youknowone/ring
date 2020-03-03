Ring
====

.. image:: https://badges.gitter.im/ring-cache/community.svg
   :alt: Join the chat at https://gitter.im/ring-cache/community
   :target: https://gitter.im/ring-cache/community?utm_source=badge&utm_medium=badge&utm_campaign=pr-badge&utm_content=badge

.. image:: https://travis-ci.org/youknowone/ring.svg?branch=master
    :target: https://travis-ci.org/youknowone/ring
.. image:: https://codecov.io/gh/youknowone/ring/graph/badge.svg
    :target: https://codecov.io/gh/youknowone/ring

Let's concentrate on code, not on storages.

Ring shows a way to control cache in point of view of code - not about storages.
Ring's decorator is convenient but also keeps fluency for general scenarios.

asyncio support for Python3.5+!

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

one key-value pair in a dictionary cache（字典中某个键值对的缓存）
-------------------------------------------------------------------
场景：由celery部署的后端框架，框架中所有job的入参、返回值格式均为dict，如下,其中，存在若干个job需要爬取入参中指定的url，
并解析页面中的数据。由于相同URL的重复访问导致大量的资源浪费，因此需要增加job的缓存，确保相同的url 60分钟只请求一次。

.. code:: python

    arg_data = {
        'taskid': 1,
        'status':True,
        'msg':'',
        'data':{
            'url':'https://www.baidu.com'
        }
    }


通过指定装饰器参数`dict_keys`实现只对data做缓存的功能。

.. code:: python

    import ring
    import redis

    rc = redis.StrictRedis()

    @ring.redis(rc, coder='json', expire=30, dict_keys='data')
    def get_url(obj):
        """very slow function
        """
        print('开始执行')
        time.sleep(1)
        return requests.get(obj['data']['url']).text


    arg_data = {
        'taskid': 160,
        'data': {
            'url': 'https://www.baidu.com'
        }
    }
    timer_non_cached = timeit.Timer("get_url({'taskid': 160,'data': {'url': 'https://www.tita.com'}})", globals=globals())
    t_non_cached = timer_non_cached.timeit(100)
    print("Non-Cached: {t_non_cached:.06f} seconds".format(t_non_cached=t_non_cached))

    timer_cached = timeit.Timer("get_url({'taskid': 161,'data': {'url': 'https://www.tita.com'}})", globals=globals())
    t_cached = timer_cached.timeit(100)
    print("Cached: {t_cached:.06f} seconds".format(t_cached=t_cached))



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

