
import ring
import pymemcache.client
import memcache
import redis
from diskcache import Cache

import pytest


pymemcache_client = pymemcache.client.Client(('127.0.0.1', 11211))
pythonmemcache_client = memcache.Client(["127.0.0.1:11211"])
redis_py_client = redis.StrictRedis()


try:
    import pylibmc
except ImportError:
    pylibmc_client = None
else:
    pylibmc_client = pylibmc.Client(['127.0.0.1'])


class StorageDict(dict):
    pass


@pytest.fixture
def storage_dict():
    storage = StorageDict()
    storage.ring = ring.func.dict
    storage.is_binary = False
    storage.has_touch = True
    return storage


@pytest.fixture(scope='session', ids=['python-memcached', 'pymemcache', 'pylibmc'], params=[
    # client, binary, has_touch
    (pythonmemcache_client, False, False),
    (pymemcache_client, True, True),
    (pylibmc_client, True, False),  # actually has_touch but not in travis
])
def memcache_client(request):
    client, is_binary, has_touch = request.param
    if client is None:
        pytest.skip()
    client.is_binary = is_binary
    client.has_touch = has_touch
    client.ring = ring.func.memcache
    return client


@pytest.fixture(scope='session', params=[
    redis_py_client,
])
def redis_client(request):
    client = request.param
    client.ring = ring.func.redis
    client.is_binary = True
    client.has_touch = True
    return client


@pytest.fixture(scope='session', params=[
    Cache('/tmp/ring-test')
])
def disk_cache(request):
    client = request.param
    client.ring = ring.func.disk
    client.is_binary = False
    client.has_touch = False
    return client


@pytest.fixture(params=[
    pytest.lazy_fixture('storage_dict'),
    pytest.lazy_fixture('memcache_client'),
    pytest.lazy_fixture('redis_client'),
    pytest.lazy_fixture('disk_cache'),
])
def storage(request):
    return request.param


@pytest.fixture(params=['function', 'method', 'class1', 'class2', 'static1', 'static2'])
def function(request, storage):
    def resultify(r):
        if storage.is_binary:
            r = str(r).encode('utf-8')
        return r

    if request.param == 'function':
        base = [0]

        @storage.ring(storage, key_prefix='', expire=10)
        def f(a, b):
            return resultify(base[0] + a * 100 + b)

        f.base = base

        return f
    else:
        class A(object):

            base = [0]

            def __ring_key__(self):
                return 'a'

            @storage.ring(storage, expire=10)
            def method(self, a, b):
                return resultify(self.base[0] + a * 100 + b)

            @storage.ring(storage, expire=10)
            @classmethod
            def cmethod(cls, a, b):
                return resultify(cls.base[0] + a * 200 + b)

            @storage.ring(storage, expire=10)
            @staticmethod
            def smethod(a, b):
                return resultify(A.base[0] + a * 200 + b)

        obj = A()
        f = {
            'method': obj.method,
            'class1': obj.cmethod,
            'class2': A.cmethod,
            'static1': obj.smethod,
            'static2': A.smethod,
        }[request.param]
        f.base = A.base
        return f


def test_common(function, storage):
    # `function` is a callable with argument `a` and `b`
    # test function is correct
    assert function.key(a=0, b=0)  # f takes a, b
    assert function.base[0] is not None  # f has attr base for test
    assert function.execute(a=1, b=2) != function.execute(a=1, b=3)  # f is not singular
    assert function.execute(a=2, b=2) != function.execute(a=1, b=2)  # f is not singular
    r = function.execute(0, 0)
    function.base[0] += 1
    assert r != function.execute(0, 0)  # base has side effect
    function.delete(1, 2)  # delete sample cache

    # test: parametrized key build
    assert function.key(1, 2) == function.key(1, b=2) == function.key(a=1, b=2)
    assert function.key(1, 2) != function.key(1, 3)

    # set base
    function.base[0] = 10000

    # test: 'get' 'execute' 'delete' 'get_or_update'
    assert None is function.get(1, 2)  # not cached yet
    r1 = function.execute(1, 2)  # run without cache

    assert r1 == function(1, 2)  # create and return cache
    assert function.get(1, 2) == function(a=1, b=2)  # cached now

    function.delete(b=2, a=1)  # delete cache
    assert function.get(1, 2) is None  # of course get fails
    assert r1 == function.get_or_update(1, 2)  # this is equivalent to call the func

    # reset base
    function.base[0] = 20000

    # test: actually cached or not
    r2 = function.execute(1, 2)
    assert r1 != r2  # base has side effect
    assert r1 == function(1, 2)  # still cached
    assert r2 != function(1, 2)

    # test: 'update'
    assert r2 == function.update(1, 2)  # immediate update

    if storage.has_touch:
        function.touch(1, 2)  # just a running test

    function.delete(1, 2)  # finallize


def test_func_dict():
    cache = {}

    base = [0]

    @ring.func.dict(cache, key_prefix='')
    def f(a, b):
        return base[0] + a * 100 + b

    assert f.key(1, 2) == ':1:2'  # dict doesn't have prefix by default

    base[0] = 10000
    assert 10102 == f(1, b=2)

    assert cache[f.key(1, 2)][1] == 10102
    assert 10103 == f(1, b=3)
    assert cache[f.key(1, 3)][1] == 10103

    base[0] = 20000
    assert 10102 == f(1, b=2)
    assert 10103 == f(1, b=3)
    assert 20204 == f(2, b=4)

    cache.clear()

    assert 20102 == f(1, b=2)
    assert 20103 == f(1, b=3)
    assert 20204 == f(2, b=4)

    base[0] = 30000
    assert 30102 == f.update(1, b=2)
    f.touch(1, b=2)


def test_func_dict_expire():
    cache = {}

    @ring.func.dict(cache, expire=1)
    def f(a, b):
        return a * 100 + b

    assert f.get(1, 2) is None
    assert f(1, 2) == 102
    assert f.update(1, 2) == 102
    f.delete(1, 2)
    assert f.get(1, 2) is None


@pytest.mark.parametrize('value', [
    1,
    0,
    True,
    False,
    u'str',
    b'bytes',
    ['list', 'with', 'values'],
    {'dict': 'also', 'matters': '!'},
    {'set', 'should', 'be', 'ordered'},
])
def test_ring_key(value):
    # test only with real cache backends. dict doesn't help this test
    @ring.func.memcache(pythonmemcache_client, expire=1)
    def simple(key):
        return key

    assert simple(value) == value  # cache miss
    assert simple(value) == value  # cache hit


def test_memcache(memcache_client):
    base = [0]

    @ring.func.memcache(memcache_client, 'ring-test')
    def f(a, b):
        r = base[0] + a * 100 + b
        sr = str(r)
        if memcache_client.is_binary:
            sr = sr.encode('utf-8')
        return sr

    f.delete(8, 6)
    assert f.key(8, 6) == 'ring-test:8:6'

    base[0] = 10000
    assert None is f.get(8, b=6)
    assert 10806 == int(f(8, b=6))
    assert 10806 == int(memcache_client.get(f.key(8, 6)))


def test_disk(disk_cache):
    base = [0]

    @ring.func.disk(disk_cache, 'ring-test')
    def f(a, b):
        r = base[0] + a * 100 + b
        sr = str(r)
        if disk_cache.is_binary:
            sr = sr.encode('utf-8')
        return sr

    f.delete(8, 6)
    assert f.key(8, 6) == 'ring-test:8:6'

    base[0] = 10000
    assert None is f.get(8, b=6)
    assert 10806 == int(f(8, b=6))
    assert 10806 == int(disk_cache.get(f.key(8, 6)))


def test_redis(redis_client):
    base = [0]

    @ring.func.redis(redis_client, 'ring-test', 5)
    def f(a, b):
        r = base[0] + a * 100 + b
        return str(r).encode('utf-8')

    assert f.key(1, 2) == 'ring-test:1:2'

    base[0] = 10000
    assert None is f.get(1, b=2)
    assert 10102 == int(f(1, b=2))
    assert 10102 == int(redis_client.get(f.key(1, 2)))


def test_common_value(storage):
    base = [b'a']

    @storage.ring(storage, key_prefix=str(storage), expire=5)
    def ff():
        base[0] += b'b'
        return base[0]

    b0 = base[0]

    # set
    v1 = ff()
    b1 = base[0]

    # get
    v2 = ff()
    b2 = base[0]

    assert b0 != b1
    assert v1 == b1
    assert v2 == b1
    assert b1 == b2

    # py3 test in asyncio
    @storage.ring(storage, key_prefix=str(storage), expire=5)
    def complicated(a, *args, **kw):
        return b'42'

    # set
    v1 = complicated(0, 1, 2, 3, b=4, c=5, d=6)
    v2 = complicated.get(0, 1, 2, 3, b=4, c=5, d=6)
    assert v1 == v2
