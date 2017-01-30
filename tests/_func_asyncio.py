
import ring
import asyncio

import pytest


@asyncio.coroutine
def common_test(f, base):
    # `f` is a callable with argument `a` and `b`
    # test f is correct
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
    assert None is ((yield from f.get(1, 2)))  # not cached yet
    r1 = yield from f.execute(1, 2)  # run without cache

    assert r1 == ((yield from f(1, 2)))  # create and return cache
    assert ((yield from f.get(1, 2))) == ((yield from f(a=1, b=2)))  # cached now

    yield from f.delete(b=2, a=1)  # delete cache
    assert ((yield from f.get(1, 2))) is None  # of course get fails
    assert r1 == ((yield from f.get_or_update(1, 2)))  # this is equivalent to call the func

    # reset base
    base[0] = 20000

    # test: actually cached or not
    r2 = ((yield from f.execute(1, 2)))
    assert r1 != r2  # base has side effect
    assert r1 == ((yield from f(1, 2)))  # still cached
    assert r2 != ((yield from f(1, 2)))

    # test: 'update'
    assert r2 == ((yield from f.update(1, 2)))  # immediate update

    yield from f.touch(1, 2)  # just a running test

    yield from f.delete(1, 2)  # finallize


@pytest.mark.asyncio
@asyncio.coroutine
def test_func_method():
    import ring.func_asyncio
    cache = {}

    class A(object):
        def __ring_key__(self):
            return 'A'

        @ring.func_asyncio.async_dict(cache)
        @asyncio.coroutine
        def method(self, a, b):
            return base + a * 100 + b

        @classmethod
        @ring.func_asyncio.async_dict(cache)
        @asyncio.coroutine
        def cmethod(cls, a, b):
            return base + a * 200 + b

    obj = A()

    base = 10000
    obj.method.delete(1, 2)
    assert ((yield from obj.method(1, 2))) == 10102

    obj.cmethod.delete(1, 2)
    assert ((yield from obj.cmethod(1, 2))) == 10202


@pytest.mark.asyncio
@asyncio.coroutine
def test_aiomcache():
    import aiomcache
    client = aiomcache.Client('127.0.0.1', 11211)

    base = [0]

    @ring.func.aiomcache(client, 'ring-test')
    @asyncio.coroutine
    def cached_function(a, b):
        return str(base[0] + a * 100 + b).encode()

    yield from common_test(cached_function, base)


@pytest.mark.asyncio
@asyncio.coroutine
def test_aioredis():
    import aioredis
    pool = yield from aioredis.create_pool(
        ('localhost', 6379),
        minsize=2, maxsize=2)

    base = [0]

    @ring.func.aioredis(pool, 'ring-test', 5)
    @asyncio.coroutine
    def cached_function(a, b):
        return str(base[0] + a * 100 + b).encode()

    yield from common_test(cached_function, base)

    pool.close()
    yield from pool.wait_closed()
