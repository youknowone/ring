
import ring


def test_func_dict():
    cache = {}

    @ring.func.dict(cache)
    def cached_function(a, b):
        return base + a * 100 + b

    assert None is cached_function.get(1, b=2)

    base = 10000
    assert 10102 == cached_function(1, b=2)
    print(cache)
    assert cache[':1:2'][1] == 10102
    assert 10103 == cached_function(1, b=3)
    assert cache[':1:3'][1] == 10103

    base = 20000
    assert 10102 == cached_function(1, b=2)
    assert 10103 == cached_function(1, b=3)
    assert 20204 == cached_function(2, b=4)

    cache.clear()

    assert 20102 == cached_function(1, b=2)
    assert 20103 == cached_function(1, b=3)
    assert 20204 == cached_function(2, b=4)

    base = 30000
    assert 30102 == cached_function.update(1, b=2)
    cached_function.touch(1, b=2)


def test_func_dict_delete():
    cache = {}

    @ring.func.dict(cache)
    def cached_function(a, b):
        return base + a * 100 + b

    base = 10000
    assert 10102 == cached_function(1, b=2)

    base = 20000
    assert 10102 == cached_function(1, b=2)

    cached_function.delete(1, b=2)

    assert 20102 == cached_function(1, b=2)


def test_pymemcache():
    import pymemcache.client
    client = pymemcache.client.Client(('127.0.0.1', 11211))

    @ring.func.memcache(client, 'ring-test')
    def cached_function(a, b):
        return base + a * 100 + b

    client.delete('ring-test:1:2')

    base = 10000
    assert None is cached_function.get(1, b=2)
    assert 10102 == int(cached_function(1, b=2))
    #assert 10102 == int(client.get('ring-test:1:2'))

    base = 20000
    assert 10102 == int(cached_function(1, b=2))

    cached_function.delete(1, b=2)

    assert 20102 == int(cached_function(1, b=2))

    cached_function.touch(1, b=2)


def test_redis():
    import redis
    client = redis.StrictRedis()

    @ring.func.redis(client, 'ring-test', 5)
    def cached_function(a, b):
        return base + a * 100 + b

    client.delete('ring-test:1:2')

    base = 10000
    assert None is cached_function.get(1, b=2)
    assert 10102 == int(cached_function(1, b=2))
    #assert 10102 == int(client.get('ring-test:1:2'))

    base = 20000
    assert 10102 == int(cached_function(1, b=2))

    cached_function.delete(1, b=2)

    assert 20102 == int(cached_function(1, b=2))

    cached_function.touch(1, b=2)
