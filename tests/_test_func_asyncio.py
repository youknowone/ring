import asyncio
import time
import sys
import shelve

import aiomcache
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
    if sys.version_info >= (3, 5):
        import aioredis
        pool_coroutine = aioredis.create_redis_pool(
            ('localhost', 6379), minsize=2, maxsize=2)
        return pool_coroutine, ring.aioredis
    else:
        pytest.skip()


@pytest.fixture()
def aioredis_connection():
    if sys.version_info <= (3, 5):
        pytest.skip()

    import aioredis

    connection_coroutine = aioredis.create_redis(
        ('localhost', 6379)
    )

    return connection_coroutine, ring.aioredis

@pytest.fixture(params=[
    lazy_fixture('storage_dict'),
    lazy_fixture('aiomcache_client'),
    lazy_fixture('aioredis_pool'),
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
@asyncio.coroutine
def test_singleton_proxy():

    @asyncio.coroutine
    def client():
        return object()

    assert ((yield from client())) is not ((yield from client()))

    proxy = ring.func.asyncio.SingletonCoroutineProxy(client())
    assert ((yield from proxy)) is ((yield from proxy))


@pytest.mark.asyncio
@asyncio.coroutine
def test_vanilla_function(aioredis_pool):
    storage, storage_ring = aioredis_pool

    with pytest.raises(TypeError):
        @storage_ring(storage)
        def vanilla_function():
            pass


@pytest.mark.asyncio
@asyncio.coroutine
def test_common(storage_and_ring):
    storage, storage_ring = storage_and_ring
    base = [0]

    @storage_ring(storage, 'ring-test !@#', 5)
    @asyncio.coroutine
    def f(a, b):
        return str(base[0] + a * 100 + b).encode()

    # `f` is a callable with argument `a` and `b`
    # test f is correct
    if asyncio.iscoroutine(storage):
        s1 = yield from f.storage.backend
        with pytest.raises(RuntimeError):
            yield from storage
        s2 = yield from f.storage.backend
        assert s1 is s2
    else:
        assert f.storage.backend is storage
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
def test_complicated_key(storage_and_ring):
    storage, storage_ring = storage_and_ring

    @storage_ring(storage)
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

    @ring.dict(cache)
    @asyncio.coroutine
    def f1(a, b):
        return a * 100 + b

    r = yield from f1.has(1, 2)
    assert r is False
    r = yield from f1(1, 2)
    assert r == 102
    r = yield from f1(1, 2)
    assert r == 102
    r = yield from f1.has(1, 2)
    assert r is True
    with pytest.raises(AttributeError):
        yield from f1.touch(1, 2)

    cache = {}

    @ring.dict(cache, expire=1)
    @asyncio.coroutine
    def f2(a, b):
        return a * 100 + b

    yield from f2(1, 2)
    yield from f2(1, 2)
    yield from f2.touch(1, 2)

    f2._rope.storage.now = lambda: time.time() + 100  # expirable duration
    assert ((yield from f2.get(1, 2))) is None


@pytest.mark.asyncio
@asyncio.coroutine
def test_many(aiomcache_client):
    client, _ = aiomcache_client

    @ring.aiomcache(client)
    @asyncio.coroutine
    def f(a):
        return 't{}'.format(a).encode()

    r = yield from f.execute_many(
        (1,),
        {'a': 2},
    )
    assert r == [b't1', b't2']

    with pytest.raises(TypeError):
        yield from f.execute_many(
            [1],
        )


@pytest.mark.asyncio
@asyncio.coroutine
def test_aiomcache(aiomcache_client):
    client, _ = aiomcache_client

    @ring.aiomcache(client)
    @asyncio.coroutine
    def f(a):
        return 't{}'.format(a).encode()

    yield from f.delete(1)
    yield from f(1)
    yield from f.touch(1)

    r = yield from f.get_many(
        (1,),
        {'a': 2},
    )
    assert r == [b't1', None]

    with pytest.raises(AttributeError):
        yield from f.has(1)

    with pytest.raises(NotImplementedError):
        yield from f.update_many()

    with pytest.raises(NotImplementedError):
        yield from f.delete_many()

    with pytest.raises(AttributeError):
        yield from f.has_many()

    with pytest.raises(AttributeError):
        yield from f.touch_many()


@pytest.mark.parametrize('expire', [
    1,
    None,
])
@pytest.mark.asyncio
@asyncio.coroutine
def test_aioredis(aioredis_pool, expire):
    client, _ = aioredis_pool

    @ring.aioredis(client, expire=expire)
    @asyncio.coroutine
    def f(a):
        return 't{}'.format(a).encode()

    yield from f.delete(1)
    yield from f.delete(2)
    yield from f.delete(3)
    r = yield from f.get(1)
    assert r is None
    r = yield from f.has(1)
    assert r is False

    yield from f(1)
    r = yield from f.has(1)
    assert r is True

    if expire is None:
        with pytest.raises(TypeError):
            yield from f.touch(1)
    else:
        yield from f.touch(1)

    # _many
    r = yield from f.get_many(
        (1,),
        {'a': 2},
    )
    assert r == [b't1', None]

    r = yield from f.update_many(
        (1,),
        {'a': 3},
    )
    assert r == [b't1', b't3']

    yield from f.set_many((
        (1,),
        (2,),
    ), (
        b'foo',
        b'bar',
    ))

    r = yield from f.get_many(
        {'a': 1},
        (2,),
        (3,),
    )
    assert r == [b'foo', b'bar', b't3']
    yield from f.delete(2)

    r = yield from f.get_or_update_many(
        (1,),
        (2,),
        (3,),
    )
    assert r == [b'foo', b't2', b't3']

    with pytest.raises(AttributeError):
        yield from f.delete_many()

    with pytest.raises(AttributeError):
        yield from f.has_many()

    with pytest.raises(AttributeError):
        yield from f.touch_many()


@pytest.mark.asyncio
@asyncio.coroutine
def test_aioredis_hash(aioredis_pool):
    client, _ = aioredis_pool

    @ring.aioredis_hash(client, 'test-hashkey')
    @asyncio.coroutine
    def f(a):
        return 't{}'.format(a).encode()

    # delete previous test
    yield from f.delete(1)
    yield from f.delete(2)
    yield from f.delete(3)

    r = yield from f.get(1)
    assert r is None

    yield from f(1)
    r = yield from f.has(1)
    assert r is True
    r = yield from f.get(1)
    assert r == b't1'

    r = yield from f.get_many(
        (1,),
        {'a': 2},
    )
    assert r == [b't1', None]

    r = yield from f.update_many(
        (1,),
        {'a': 3},
    )
    assert r == [b't1', b't3']

    yield from f.set_many((
        (1,),
        (2,),
    ), (
        b'foo',
        b'bar',
    ))

    r = yield from f.get_many(
        {'a': 1},
        (2,),
        (3,),
    )
    assert r == [b'foo', b'bar', b't3']
    yield from f.delete(2)

    r = yield from f.get_or_update_many(
        (1,),
        (2,),
        (3,),
    )
    assert r == [b'foo', b't2', b't3']


@pytest.mark.asyncio
@asyncio.coroutine
def test_func_method(storage_dict):
    storage, _ = storage_dict

    class A(object):
        def __ring_key__(self):
            return 'A'

        @ring.dict(storage)
        @asyncio.coroutine
        def method(self, a, b):
            return base + a * 100 + b

        @ring.dict(storage)
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


@pytest.mark.asyncio
@asyncio.coroutine
def test_forced_sync(synchronous_storage_and_ring):
    storage, storage_ring = synchronous_storage_and_ring

    with pytest.raises(TypeError):
        @storage_ring(storage)
        @asyncio.coroutine
        def g():
            return 1

    @storage_ring(storage, force_asyncio=True)
    @asyncio.coroutine
    def f(a):
        return a

    yield from f.delete('a')
    assert None is ((yield from f.get('a')))
    assert 'a' == ((yield from f('a')))
    assert 'a' == ((yield from f.get('a')))
