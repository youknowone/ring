import sys
import time
import shelve
import ring
import pymemcache.client
import memcache
import redis
import diskcache
from ring.func.lru_cache import LruCache

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
    storage.ring = ring.dict
    storage.is_binary = False
    storage.has_has = True
    storage.has_touch = True
    storage.has_expire = True
    return storage


@pytest.fixture
def storage_shelve():
    storage = shelve.open('/tmp/ring-test/shelve{}'.format(sys.version_info[0]))
    storage.ring = ring.shelve
    storage.is_binary = False
    storage.has_has = True
    storage.has_touch = False
    storage.has_expire = False
    return storage


@pytest.fixture
def storage_lru():
    storage = LruCache(128)
    storage.ring = ring.lru
    storage.is_binary = False
    storage.has_has = True
    storage.has_touch = True
    storage.has_expire = False
    return storage


@pytest.fixture(scope='session', params=[
    diskcache.Cache('/tmp/ring-test/diskcache')
])
def storage_diskcache(request):
    client = request.param
    client.ring = ring.disk
    client.is_binary = False
    client.has_has = False
    client.has_touch = False
    client.has_expire = True
    return client


@pytest.fixture(scope='session', ids=['python-memcached', 'pymemcache', 'pylibmc'], params=[
    # client, binary, has_touch
    (pythonmemcache_client, False, sys.version_info[0] == 2),
    (pymemcache_client, True, True),
    (pylibmc_client, True, None),  # actually has_touch but not in travis
])
def memcache_client(request):
    client, is_binary, has_touch = request.param
    if client is None:
        pytest.skip()
    client.is_binary = is_binary
    client.has_has = False
    client.has_touch = has_touch
    client.has_expire = True
    client.ring = ring.memcache
    return client


@pytest.fixture(scope='session', params=[
    redis_py_client,
])
def redis_client(request):
    client = request.param
    client.ring = ring.redis
    client.is_binary = True
    client.has_has = True
    client.has_touch = True
    client.has_expire = True
    return client


@pytest.fixture(params=[
    pytest.lazy_fixture('storage_dict'),
    pytest.lazy_fixture('storage_shelve'),
    pytest.lazy_fixture('storage_lru'),
    pytest.lazy_fixture('memcache_client'),
    pytest.lazy_fixture('redis_client'),
    pytest.lazy_fixture('storage_diskcache'),
])
def storage(request):
    return request.param


@pytest.fixture(params=['function', 'method1', 'method2', 'class1', 'class2', 'static1', 'static2'])
def function(request, storage):
    def resultify(r):
        if storage.is_binary:
            r = str(r).encode('utf-8')
        return r

    options = {'wire_slots': ('base',)}
    if storage.has_expire:
        options['expire'] = 10

    if request.param == 'function':
        base = [0]

        @storage.ring(storage, **options)
        def f(a, b):
            return resultify(base[0] + a * 100 + b)

        f.base = base

        return f
    else:
        class A(object):

            base = [0]

            def __ring_key__(self):
                return 'a'

            @storage.ring(storage, **options)
            def method(self, a, b):
                return resultify(self.base[0] + a * 100 + b)

            @storage.ring(storage, **options)
            @classmethod
            def cmethod(cls, a, b):
                return resultify(cls.base[0] + a * 200 + b)

            @storage.ring(storage, **options)
            @staticmethod
            def smethod(a, b):
                return resultify(A.base[0] + a * 200 + b)

        obj1 = A()
        obj2 = A()
        f = {
            'method1': obj1.method,
            'method2': obj2.method,
            'class1': obj1.cmethod,
            'class2': A.cmethod,
            'static1': obj1.smethod,
            'static2': A.smethod,
        }[request.param]
        f.base = A.base
        return f


def test_common(function, storage):
    # `function` is a callable with parameter `a` and `b`
    # test function is correct
    assert function.storage.backend is storage
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

    if storage.has_has:
        assert function.has(1, 2) is True
        assert function.has(5, 9) is False

    if storage.has_touch:
        function.touch(1, 2)  # just a running test
        function.touch(0, 0)  # illegal touch
    elif storage.has_touch is not None:  # None means unknown
        with pytest.raises((AttributeError, NotImplementedError)):
            function.touch(1, 2)

    function.set(b'RANDOMVALUE', 1, 2)
    assert function.get(1, 2) == b'RANDOMVALUE'

    function.delete(1, 2)  # finallize


def test_func_dict():
    cache = {}

    base = [0]

    @ring.dict(cache, key_prefix='', expire=10)
    def f(a, b):
        return base[0] + a * 100 + b

    assert f.key(1, 2) == ':1:2'  # dict doesn't have prefix by default

    base[0] = 10000
    assert False is f.has(1, 2)
    assert 10102 == f(1, b=2)
    assert True is f.has(1, 2)

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

    f._rope.storage.now = lambda: time.time() + 100  # expirable duration
    assert f.get(1, b=2) is None


def test_func_dict_without_expiration():
    @ring.dict({})
    def f():
        return 0

    assert f.get() is None
    assert f() == 0
    with pytest.raises(AttributeError):
        f.touch()


def test_func_dict_expire():
    cache = {}

    @ring.dict(cache, expire=1)
    def f(a, b):
        return a * 100 + b

    assert f.get(1, 2) is None
    assert f(1, 2) == 102
    assert f.update(1, 2) == 102
    f.delete(1, 2)
    assert f.get(1, 2) is None


def test_lru(storage_lru):
    @ring.lru(maxsize=2)
    def f(a, b):
        return a * 100 + b

    assert 102 == f(1, 2)
    assert 205 == f(2, 5)
    assert 102 == f.get(1, 2)
    assert 205 == f.get(2, 5)

    assert 503 == f(5, 3)
    assert None is f.get(1, 2)


def test_diskcache(storage_diskcache):
    base = [0]

    @ring.disk(storage_diskcache, 'ring-test')
    def f(a, b):
        r = base[0] + a * 100 + b
        sr = str(r)
        if storage_diskcache.is_binary:
            sr = sr.encode('utf-8')
        return sr

    f.delete(8, 6)
    assert f.key(8, 6) == 'ring-test:8:6'

    base[0] = 10000
    assert None is f.get(8, b=6)
    assert 10806 == int(f(8, b=6))
    assert 10806 == int(storage_diskcache.get(f.key(8, 6)))

    with pytest.raises(AttributeError):
        f.touch(0, 0)


def test_common_value(storage):
    options = {'expire': 10}
    if not storage.has_expire:
        options = {}

    base = [b'a']

    @storage.ring(storage, key_prefix=str(storage), **options)
    def ff():
        base[0] += b'b'
        return base[0]

    ff.delete()

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
    @storage.ring(storage, key_prefix=str(storage), **options)
    def complicated(a, *args, **kw):
        return b'42'

    # set
    v1 = complicated(0, 1, 2, 3, b=4, c=5, d=6)
    v2 = complicated.get(0, 1, 2, 3, b=4, c=5, d=6)
    assert v1 == v2


def test_execute_many(redis_client):
    client = redis_client

    @ring.memcache(client, coder='json')
    def f(a):
        return a

    r = f.execute_many(
        (1, ),
        (2, ),
    )
    assert r == [1, 2]

    with pytest.raises(TypeError):
        f.execute_many([1])
