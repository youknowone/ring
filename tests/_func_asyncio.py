
import ring
import asyncio

import pytest


@pytest.mark.asyncio
@asyncio.coroutine
def test_func_method():
    import ring.func_asyncio
    cache = {}

    class A(object):
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

    @ring.func.aiomcache(client, 'ring-test')
    @asyncio.coroutine
    def cached_function(a, b):
        return str(base + a * 100 + b).encode()

    yield from client.delete(b'ring-test:1:2')

    base = 10000
    assert None is (yield from cached_function.get(1, b=2))
    assert 10102 == int((yield from cached_function(1, b=2)))
    assert 10102 == int((yield from client.get(b'ring-test:1:2')))

    base = 20000
    assert 10102 == int((yield from cached_function(1, b=2)))

    yield from cached_function.delete(1, b=2)

    assert 20102 == int((yield from cached_function(1, b=2)))

    yield from cached_function.touch(1, b=2)


@pytest.mark.asyncio
@asyncio.coroutine
def test_aioredis():
    import aioredis
    pool = yield from aioredis.create_pool(
        ('localhost', 6379),
        minsize=2, maxsize=2)

    @ring.func.aioredis(pool, 'ring-test', 5)
    @asyncio.coroutine
    def cached_function(a, b):
        return str(base + a * 100 + b).encode()

    base = 10000
    yield from cached_function.delete(1, b=2)
    assert None is (yield from cached_function.get(1, b=2))
    assert 10102 == int((yield from cached_function(1, b=2)))

    base = 20000
    assert 10102 == int((yield from cached_function(1, b=2)))

    yield from cached_function.delete(1, b=2)

    assert 20102 == int((yield from cached_function(1, b=2)))

    yield from cached_function.touch(1, b=2)

    pool.close()
    yield from pool.wait_closed()
