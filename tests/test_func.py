
import ring
import pymemcache.client
import memcache
import redis

import pytest


pymemcache_client = pymemcache.client.Client(('127.0.0.1', 11211))
memcache_client = memcache.Client(["127.0.0.1:11211"])
redis_client = redis.StrictRedis()

try:
    import pylibmc
except ImportError:
    pylibmc_client = None
else:
    pylibmc_client = pylibmc.Client(['127.0.0.1'])


def common_test(f, base, has_touch=True):
    # `f` is a callable with argument `a` and `b`
    # test f is correct
    assert f.key(a=0, b=0)  # f takes a, b
    assert base[0] is not None  # f has attr base for test
    assert f.execute(a=1, b=2) != f.execute(a=1, b=3)  # f is not singular
    assert f.execute(a=2, b=2) != f.execute(a=1, b=2)  # f is not singular
    r = f.execute(0, 0)
    base[0] += 1
    assert r != f.execute(0, 0)  # base has side effect
    f.delete(1, 2)  # delete sample cache

    # test: parametrized key build
    assert f.key(1, 2) == f.key(1, b=2) == f.key(a=1, b=2)
    assert f.key(1, 2) != f.key(1, 3)

    # set base
    base[0] = 10000

    # test: 'get' 'execute' 'delete' 'get_or_update'
    assert None is f.get(1, 2)  # not cached yet
    r1 = f.execute(1, 2)  # run without cache

    assert r1 == f(1, 2)  # create and return cache
    assert f.get(1, 2) == f(a=1, b=2)  # cached now

    f.delete(b=2, a=1)  # delete cache
    assert f.get(1, 2) is None  # of course get fails
    assert r1 == f.get_or_update(1, 2)  # this is equivalent to call the func

    # reset base
    base[0] = 20000

    # test: actually cached or not
    r2 = f.execute(1, 2)
    assert r1 != r2  # base has side effect
    assert r1 == f(1, 2)  # still cached
    assert r2 != f(1, 2)

    # test: 'update'
    assert r2 == f.update(1, 2)  # immediate update

    if has_touch:
        f.touch(1, 2)  # just a running test

    f.delete(1, 2)  # finallize


def test_func_dict():
    cache = {}

    base = [0]

    @ring.func.dict(cache, key_prefix='')
    def f(a, b):
        return base[0] + a * 100 + b

    common_test(f, base)

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
    set(['set', 'should', 'be', 'ordered']),
])
def test_ring_key(value):
    # test only with real cache backends. dict doesn't help this
    @ring.func.memcache(memcache_client)
    def simple(key):
        return key

    assert simple(value) == value  # cache miss
    assert simple(value) == value  # cache hit


def test_func_dict_method():
    cache = {}

    class A(object):

        base = [0]

        def __ring_key__(self):
            return 'A'

        @ring.func.dict(cache)
        def method(self, a, b):
            return self.base[0] + a * 100 + b

        @classmethod
        @ring.func.dict(cache)
        def cmethod(cls, a, b):
            # cls can be None
            return A.base[0] + a * 200 + b

    obj = A()
    common_test(obj.method, A.base)
    common_test(obj.cmethod, A.base)
    common_test(A.cmethod, A.base)


@pytest.mark.parametrize('client,binary,has_touch', [
    (memcache_client, False, False),
    (pymemcache_client, True, True),
    (pylibmc_client, True, False),  # actually has_touch but not in travis
])
def test_memcache(client, binary, has_touch):
    if client is None:
        pytest.skip()

    base = [0]

    @ring.func.memcache(client, 'ring-test')
    def f(a, b):
        r = base[0] + a * 100 + b
        sr = str(r)
        if binary:
            sr = sr.encode('utf-8')
        return sr

    common_test(f, base, has_touch)

    assert f.key(1, 2) == 'ring-test:1:2'

    base[0] = 10000
    assert None is f.get(1, b=2)
    assert 10102 == int(f(1, b=2))
    assert 10102 == int(client.get(f.key(1, 2)))


def test_redis():
    client = redis_client

    base = [0]

    @ring.func.redis(client, 'ring-test', 5)
    def f(a, b):
        r = base[0] + a * 100 + b
        return str(r).encode('utf-8')

    common_test(f, base)

    assert f.key(1, 2) == 'ring-test:1:2'

    base[0] = 10000
    assert None is f.get(1, b=2)
    assert 10102 == int(f(1, b=2))
    assert 10102 == int(client.get(f.key(1, 2)))


def test_unexisting_coder():
    cache = {}

    with pytest.raises(TypeError):
        @ring.func.dict(cache, coder='messed-up')
        def f():
            pass


def test_unexisting_ring_key():
    cache = {}

    class A(object):
        @ring.func.dict(cache)
        def f(self):
            return 0

    a = A()
    with pytest.raises(TypeError):
        a.f()


def common_value_test(deco):
    base = ['a']

    @deco
    def ff():
        base[0] += 'a'
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


@pytest.mark.parametrize('client', [
    (memcache_client),
    (pymemcache_client),
    (pylibmc_client),
])
def test_value_memcache(client):
    if client is None:
        pytest.skip()
    deco = ring.func.memcache(client, key_prefix=str(client), time=5)
    common_value_test(deco)


def test_value_redis():
    deco = ring.func.redis(redis_client, key_prefix=str(redis_client), expire=5)
    common_value_test(deco)


def test_value_dict():
    deco = ring.func.dict({}, key_prefix='', expire=5)
    common_value_test(deco)
