import asyncio
import time
import sys
import shelve
from typing import Optional

import aiomcache
import aioredis
import diskcache
import ring
from ring.func.lru_cache import LruCache

import pytest
from pytest_lazyfixture import lazy_fixture

from tests.test_func_sync import StorageDict


class AiomcacheProxy(object):

    _aiomcache_clients = {}

    def __getattr__(self, key):
        _aiomcache_clients = AiomcacheProxy._aiomcache_clients
        loop_key = id(asyncio.get_event_loop())
        if loop_key not in _aiomcache_clients:
            _aiomcache_clients[loop_key] = aiomcache.Client('127.0.0.1', 11211)
        client = _aiomcache_clients[loop_key]

        return getattr(client, key)


@pytest.fixture()
def storage_dict():
    storage = StorageDict()
    return storage, ring.dict


@pytest.fixture()
def aiomcache_client():
    client = AiomcacheProxy()
    return client, ring.func.asyncio.aiomcache


@pytest.fixture()
def aioredis_pool():
    if sys.version_info <= (3, 5):
        pytest.skip()

    pool = aioredis.from_url(
        "redis://localhost", encoding="utf-8",
    )
    return pool, ring.aioredis


@pytest.fixture()
def aioredis_connection():
    if sys.version_info <= (3, 5):
        pytest.skip()

    pool = aioredis.from_url(
        "redis://localhost", encoding="utf-8",
    )
    return pool, ring.aioredis
    pool = aioredis_pool()[0]
    return pool.client(), ring.aioredis


@pytest.fixture(params=[
    lazy_fixture('aioredis_connection'),
    lazy_fixture('aioredis_pool'),
])
def aioredis_client(request):
    return request.param


@pytest.fixture(params=[
    lazy_fixture('storage_dict'),
    lazy_fixture('aiomcache_client'),
    lazy_fixture('aioredis_pool'),
    lazy_fixture('aioredis_connection')
])
def storage_and_ring(request):
    return request.param


@pytest.fixture()
def storage_lru():
    return LruCache(128), ring.lru


@pytest.fixture()
def storage_shelve():
    storage = shelve.open('/tmp/ring-test/shelvea')
    return storage, ring.shelve


@pytest.fixture()
def storage_disk(request):
    client = diskcache.Cache('/tmp/ring-test/diskcache')
    return client, ring.disk


@pytest.fixture(params=[
    lazy_fixture('storage_lru'),
    lazy_fixture('storage_shelve'),
    lazy_fixture('storage_disk'),
])
def synchronous_storage_and_ring(request):
    return request.param


@pytest.mark.asyncio
async def test_singleton_proxy():

    async def client():
        return object()

    assert (await client()) is not (await client())

    proxy = ring.func.asyncio.SingletonCoroutineProxy(client())
    assert (await proxy) is (await proxy)


@pytest.mark.asyncio
async def test_vanilla_function(aioredis_client):
    storage, storage_ring = aioredis_client

    with pytest.raises(TypeError):
        @storage_ring(storage)
        def vanilla_function():
            pass


@pytest.mark.asyncio
async def test_common(storage_and_ring):
    storage, storage_ring = storage_and_ring
    base = [0]

    @storage_ring(storage, 'ring-test !@#', 5)
    async def f(a, b):
        return str(base[0] + a * 100 + b).encode()

    # `f` is a callable with argument `a` and `b`
    # test f is correct
    if asyncio.iscoroutine(storage):
        s1 = await f.storage.backend
        with pytest.raises(RuntimeError):
            await storage
        s2 = await f.storage.backend
        assert s1 is s2
    else:
        assert f.storage.backend is storage
    assert f.key(a=0, b=0)  # f takes a, b
    assert base[0] is not None  # f has attr base for test
    assert (await f.execute(a=1, b=2)) != (await f.execute(a=1, b=3))  # f is not singular
    assert (await f.execute(a=2, b=2)) != (await f.execute(a=1, b=2))  # f is not singular
    r = await f.execute(0, 0)
    base[0] += 1
    assert r != (await f.execute(0, 0))  # base has side effect
    await f.delete(1, 2)  # delete sample cache

    # test: parametrized key build
    assert f.key(1, 2) == f.key(1, b=2) == f.key(a=1, b=2)
    assert f.key(1, 2) != f.key(1, 3)

    # set base
    base[0] = 10000

    # test: 'get' 'execute' 'delete' 'get_or_update'
    rn = await f.get(1, 2)
    assert rn is None, (rn, f.key(1, 2))  # not cached yet
    r1 = await f.execute(1, 2)  # run without cache

    r2 = await f(1, 2)
    assert r1 == r2, (r1, r2)  # create and return cache
    assert (await f.get(1, 2)) == (await f(a=1, b=2))  # cached now

    await f.delete(b=2, a=1)  # delete cache
    assert (await f.get(1, 2)) is None  # of course get fails
    assert r1 == (await f.get_or_update(1, 2))  # this is equivalent to call the func

    # reset base
    base[0] = 20000

    # test: actually cached or not
    r3 = await f.execute(1, 2)
    assert r1 != r3  # base has side effect
    assert r1 == (await f(1, 2))  # still cached
    assert r3 != (await f(1, 2))

    # test: 'update'
    assert r3 == (await f.update(1, 2))  # immediate update

    await f.touch(1, 2)  # just a running test
    await f.touch(0, 0)  # illegal access

    await f.set(b'RANDOMVALUE', 1, 2)
    rset = await f.get(1, 2)
    assert rset == b'RANDOMVALUE'

    await f.delete(1, 2)  # finallize


@pytest.mark.asyncio
async def test_complicated_key(storage_and_ring):
    storage, storage_ring = storage_and_ring

    @storage_ring(storage)
    async def complicated(a, *args, b, **kw):
        return b'42'

    # set
    v1 = await complicated(0, 1, 2, 3, b=4, c=5, d=6)
    v2 = await complicated.get(0, 1, 2, 3, b=4, c=5, d=6)
    assert v1 == v2, (v1, v2)


@pytest.mark.asyncio
async def test_func_dict():
    cache = {}

    @ring.dict(cache)
    async def f1(a, b):
        return a * 100 + b

    r = await f1.has(1, 2)
    assert r is False
    r = await f1(1, 2)
    assert r == 102
    r = await f1(1, 2)
    assert r == 102
    r = await f1.has(1, 2)
    assert r is True
    with pytest.raises(AttributeError):
        await f1.touch(1, 2)

    cache = {}

    @ring.dict(cache, expire=1)
    async def f2(a, b):
        return a * 100 + b

    await f2(1, 2)
    await f2(1, 2)
    await f2.touch(1, 2)

    f2._rope.storage.now = lambda: time.time() + 100  # expirable duration
    assert (await f2.get(1, 2)) is None


@pytest.mark.asyncio
async def test_many(aiomcache_client):
    client, _ = aiomcache_client

    @ring.aiomcache(client)
    async def f(a):
        return 't{}'.format(a).encode()

    r = await f.execute_many(
        (1,),
        {'a': 2},
    )
    assert r == [b't1', b't2']

    with pytest.raises(TypeError):
        await f.execute_many(
            [1],
        )


@pytest.mark.asyncio
async def test_aiomcache(aiomcache_client):
    client, _ = aiomcache_client

    @ring.aiomcache(client)
    async def f(a):
        return 't{}'.format(a).encode()

    await f.delete(1)
    await f(1)
    await f.touch(1)

    r = await f.get_many(
        (1,),
        {'a': 2},
    )
    assert r == [b't1', None]

    with pytest.raises(AttributeError):
        await f.has(1)

    with pytest.raises(NotImplementedError):
        await f.update_many()

    with pytest.raises(NotImplementedError):
        await f.delete_many()

    with pytest.raises(AttributeError):
        await f.has_many()

    with pytest.raises(AttributeError):
        await f.touch_many()


@pytest.mark.parametrize('expire', [
    1,
    None,
])
@pytest.mark.asyncio
async def test_aioredis(aioredis_client, expire):
    client, _ = aioredis_client

    @ring.aioredis(client, expire=expire)
    async def f(a):
        return 't{}'.format(a).encode()

    await f.delete(1)
    await f.delete(2)
    await f.delete(3)
    r = await f.get(1)
    assert r is None
    r = await f.has(1)
    assert r is False

    await f(1)
    r = await f.has(1)
    assert r is True

    if expire is None:
        with pytest.raises(TypeError):
            await f.touch(1)
    else:
        await f.touch(1)

    # _many
    r = await f.get_many(
        (1,),
        {'a': 2},
    )
    assert r == [b't1', None]

    r = await f.update_many(
        (1,),
        {'a': 3},
    )
    assert r == [b't1', b't3']

    await f.set_many((
        (1,),
        (2,),
    ), (
        b'foo',
        b'bar',
    ))

    r = await f.get_many(
        {'a': 1},
        (2,),
        (3,),
    )
    assert r == [b'foo', b'bar', b't3']
    await f.delete(2)

    r = await f.get_or_update_many(
        (1,),
        (2,),
        (3,),
    )
    assert r == [b'foo', b't2', b't3']

    with pytest.raises(AttributeError):
        await f.delete_many()

    with pytest.raises(AttributeError):
        await f.has_many()

    with pytest.raises(AttributeError):
        await f.touch_many()


@pytest.mark.asyncio
async def test_aioredis_hash(aioredis_client):
    client, _ = aioredis_client

    @ring.aioredis_hash(client, 'test-hashkey')
    async def f(a):
        return 't{}'.format(a).encode()

    # delete previous test
    await f.delete(1)
    await f.delete(2)
    await f.delete(3)

    r = await f.get(1)
    assert r is None

    await f(1)
    r = await f.has(1)
    assert r is True
    r = await f.get(1)
    assert r == b't1'

    r = await f.get_many(
        (1,),
        {'a': 2},
    )
    assert r == [b't1', None]

    r = await f.update_many(
        (1,),
        {'a': 3},
    )
    assert r == [b't1', b't3']

    await f.set_many((
        (1,),
        (2,),
    ), (
        b'foo',
        b'bar',
    ))

    r = await f.get_many(
        {'a': 1},
        (2,),
        (3,),
    )
    assert r == [b'foo', b'bar', b't3']
    await f.delete(2)

    r = await f.get_or_update_many(
        (1,),
        (2,),
        (3,),
    )
    assert r == [b'foo', b't2', b't3']


@pytest.mark.asyncio
async def test_func_method(storage_dict):
    storage, _ = storage_dict

    class A(object):
        def __ring_key__(self):
            return 'A'

        @ring.dict(storage)
        async def method(self, a, b):
            return base + a * 100 + b

        @ring.dict(storage)
        @classmethod
        async def cmethod(cls, a, b):
            return base + a * 200 + b

    obj = A()

    base = 10000
    await obj.method.delete(1, 2)
    assert (await obj.method(1, 2)) == 10102

    await obj.cmethod.delete(1, 2)
    assert (await obj.cmethod(1, 2)) == 10202

    await A.cmethod.delete(1, 2)
    assert (await A.cmethod(1, 2)) == 10202

    assert obj.cmethod.key(3, 4) == A.cmethod.key(3, 4)


@pytest.mark.asyncio
async def test_forced_sync(synchronous_storage_and_ring):
    storage, storage_ring = synchronous_storage_and_ring

    with pytest.raises(TypeError):
        @storage_ring(storage)
        async def g():
            return 1

    @storage_ring(storage, force_asyncio=True)
    async def f(a):
        return a

    await f.delete('a')
    assert None is (await f.get('a'))
    assert 'a' == (await f('a'))
    assert 'a' == (await f.get('a'))


@pytest.mark.asyncio
async def test_async_def_func_method():
    cache = {}

    async def async_func(n):
        return n

    class A(object):
        def __str__(self):
            return 'A'

        @ring.dict(cache)
        async def method(self, a, b):
            x = await async_func(100)
            return base + a * x + b

        @ring.dict(cache)
        @classmethod
        async def cmethod(cls, a, b):
            x = await async_func(200)
            return base + a * x + b

    obj = A()

    base = 10000
    await obj.method.delete(1, 2)
    value = await obj.method(1, 2)
    assert value == 10102, value

    await obj.cmethod.delete(1, 2)
    value = await obj.cmethod(1, 2)
    assert value == 10202, value


@pytest.mark.parametrize('field,expected', [
    (None, {'a': int, 'b': str, 'return': float}),
    ('__call__', {'a': int, 'b': str, 'return': float}),
    ('execute', {'a': int, 'b': str, 'return': float}),
    ('get', {'a': int, 'b': str, 'return': Optional[float]}),
    ('get_or_update', {'a': int, 'b': str, 'return': float}),
    ('update', {'a': int, 'b': str, 'return': float}),
    ('key', {'a': int, 'b': str, 'return': str}),
    ('set', {'a': int, 'b': str, 'return': None}),
    ('delete', {'a': int, 'b': str, 'return': None}),
    ('touch', {'a': int, 'b': str, 'return': None}),

])
@pytest.mark.asyncio
async def test_annotation(field, expected):

    @ring.dict({})
    def f(a: int, b: str) -> float:
        pass

    @ring.dict({})
    async def g(a: int, b: str) -> float:
        pass

    if field is not None:
        owner = getattr(f, field)
    else:
        owner = f

    print('actual:', owner.__annotations__)
    print('expected:', expected)
    assert owner.__annotations__ == expected

    if field is not None:
        owner = getattr(g, field)
    else:
        owner = g

    print('actual:', owner.__annotations__)
    print('expected:', expected)
    assert owner.__annotations__ == expected
