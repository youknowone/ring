
import ring
import asyncio
import aiomcache

import pytest

from tests.test_func_sync import StorageDict


@pytest.fixture()
@asyncio.coroutine
def storage_dict():
    storage = StorageDict()
    storage.ring = ring.aiodict
    return storage


@pytest.fixture()
@asyncio.coroutine
def aiomcache_client():
    client = aiomcache.Client('127.0.0.1', 11211)
    client.ring = ring.func.aiomcache
    return client


@pytest.fixture()
@asyncio.coroutine
def aioredis_pool():
    import sys

    if sys.version_info >= (3, 5):
        import aioredis

        global _aioredis_pool
        _aioredis_pool = yield from aioredis.create_redis_pool(
            ('localhost', 6379), minsize=2, maxsize=2)
        _aioredis_pool.ring = ring.func.aioredis
        return _aioredis_pool

    else:
        pytest.skip()


@pytest.fixture(params=[
    pytest.lazy_fixture('storage_dict'),
    pytest.lazy_fixture('aiomcache_client'),
    pytest.lazy_fixture('aioredis_pool'),
])
def gen_storage(request):
    return request.param


@pytest.mark.asyncio
@asyncio.coroutine
def test_vanilla_function(storage_dict):
    storage = yield from storage_dict

    with pytest.raises(TypeError):
        @storage.ring(storage)
        def vanilla_function():
            pass


@pytest.mark.asyncio
@asyncio.coroutine
def test_common(gen_storage):
    storage = yield from gen_storage
    base = [0]

    @storage.ring(storage, 'ring-test !@#', 5)
    @asyncio.coroutine
    def f(a, b):
        return str(base[0] + a * 100 + b).encode()

    # `f` is a callable with argument `a` and `b`
    # test f is correct
    assert f.ring.storage is storage
    assert f.key(a=0, b=0)  # f takes a, b
    assert base[0] is not None  # f has attr base for test
    assert ((yield from f.execute(a=1, b=2))) != ((yield from f.execute(a=1, b=3)))  # f is not singular
    assert ((yield from f.execute(a=2, b=2))) != ((yield from f.execute(a=1, b=2)))  # f is not singular
    r = yield from f.execute(0, 0)
    base[0] += 1
    assert r != ((yield from f.execute(0, 0)))  # base has side effect
    yield from f.delete(1, 2)  # delete sample cache

    # test: parametrized key build
    assert f.key(1, 2) == f.key(1, b=2) == f.key(a=1, b=2)
    assert f.key(1, 2) != f.key(1, 3)

    # set base
    base[0] = 10000

    # test: 'get' 'execute' 'delete' 'get_or_update'
    rn = yield from f.get(1, 2)
    assert rn is None, (rn, f.key(1, 2))  # not cached yet
    r1 = yield from f.execute(1, 2)  # run without cache

    r2 = yield from f(1, 2)
    assert r1 == r2, (r1, r2)  # create and return cache
    assert ((yield from f.get(1, 2))) == ((yield from f(a=1, b=2)))  # cached now

    yield from f.delete(b=2, a=1)  # delete cache
    assert ((yield from f.get(1, 2))) is None  # of course get fails
    assert r1 == ((yield from f.get_or_update(1, 2)))  # this is equivalent to call the func

    # reset base
    base[0] = 20000

    # test: actually cached or not
    r3 = yield from f.execute(1, 2)
    assert r1 != r3  # base has side effect
    assert r1 == ((yield from f(1, 2)))  # still cached
    assert r3 != ((yield from f(1, 2)))

    # test: 'update'
    assert r3 == ((yield from f.update(1, 2)))  # immediate update

    yield from f.touch(1, 2)  # just a running test
    yield from f.touch(0, 0)  # illegal access

    yield from f.set(b'RANDOMVALUE', 1, 2)
    rset = yield from f.get(1, 2)
    assert rset == b'RANDOMVALUE'

    yield from f.delete(1, 2)  # finallize


@pytest.mark.asyncio
@asyncio.coroutine
def test_complicated_key(gen_storage):

    storage = yield from gen_storage

    @storage.ring(storage)
    @asyncio.coroutine
    def complicated(a, *args, b, **kw):
        return b'42'

    # set
    v1 = yield from complicated(0, 1, 2, 3, b=4, c=5, d=6)
    v2 = yield from complicated.get(0, 1, 2, 3, b=4, c=5, d=6)
    assert v1 == v2, (v1, v2)


@pytest.mark.asyncio
@asyncio.coroutine
def test_func_dict():
    cache = {}

    @ring.aiodict(cache)
    @asyncio.coroutine
    def f1(a, b):
        return a * 100 + b

    yield from f1(1, 2)
    yield from f1(1, 2)

    cache = {}

    @ring.aiodict(cache, expire=1)
    @asyncio.coroutine
    def f2(a, b):
        return a * 100 + b

    yield from f2(1, 2)
    yield from f2(1, 2)


@pytest.mark.asyncio
@asyncio.coroutine
def test_func_method(storage_dict):
    storage = yield from storage_dict

    class A(object):
        def __ring_key__(self):
            return 'A'

        @ring.aiodict(storage)
        @asyncio.coroutine
        def method(self, a, b):
            return base + a * 100 + b

        @ring.aiodict(storage)
        @classmethod
        @asyncio.coroutine
        def cmethod(cls, a, b):
            return base + a * 200 + b

    obj = A()

    base = 10000
    yield from obj.method.delete(1, 2)
    assert ((yield from obj.method(1, 2))) == 10102

    yield from obj.cmethod.delete(1, 2)
    assert ((yield from obj.cmethod(1, 2))) == 10202

    yield from A.cmethod.delete(1, 2)
    assert ((yield from A.cmethod(1, 2))) == 10202

    assert obj.cmethod.key(3, 4) == A.cmethod.key(3, 4)
