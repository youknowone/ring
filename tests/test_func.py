
import ring


def test_func_dict():
    cache = {}

    @ring.func.dict(cache, key_prefix='')
    def f(a, b):
        return base + a * 100 + b

    assert None is f.get(1, b=2)

    base = 10000
    assert 10102 == f(1, b=2)

    assert f.key(1, 2) == ':1:2'
    assert f.key(1, b=2) == ':1:2'
    assert f.key(a=1, b=2) == ':1:2'

    assert cache[f.key(1, 2)][1] == 10102
    assert 10103 == f(1, b=3)
    assert cache[f.key(1, 3)][1] == 10103

    base = 20000
    assert 10102 == f(1, b=2)
    assert 10103 == f(1, b=3)
    assert 20204 == f(2, b=4)

    cache.clear()

    assert 20102 == f(1, b=2)
    assert 20103 == f(1, b=3)
    assert 20204 == f(2, b=4)

    base = 30000
    assert 30102 == f.update(1, b=2)
    f.touch(1, b=2)


def test_func_method():
    cache = {}

    class A(object):
        def __ring_key__(self):
            return 'A'

        @ring.func.dict(cache)
        def method(self, a, b):
            return base + a * 100 + b

        @classmethod
        @ring.func.dict(cache)
        def cmethod(cls, a, b):
            return base + a * 200 + b

    obj = A()

    base = 10000
    obj.method.delete(1, 2)
    assert obj.method(1, 2) == 10102

    obj.cmethod.delete(1, 2)
    assert obj.cmethod(1, 2) == 10202


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
    assert 10102 == int(client.get('ring-test:1:2'))

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
    assert 10102 == int(client.get('ring-test:1:2'))

    base = 20000
    assert 10102 == int(cached_function(1, b=2))

    cached_function.delete(1, b=2)

    assert 20102 == int(cached_function(1, b=2))

    cached_function.touch(1, b=2)
