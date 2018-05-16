""":mod:`ring.func_asyncio`

Collection of asyncio factory functions.
"""
import asyncio
import inspect
import functools
import time
from ring import func_base as fbase

__all__ = ('dict', 'aiodict', 'aiomcache', 'aioredis', )

inspect_iscoroutinefunction = getattr(inspect, 'iscoroutinefunction', lambda f: False)


def ring_factory(
        c, storage_instance, ckey, RingBase,
        Interface, StorageImplementation,
        miss_value, expire_default, coder):

    if not c.is_coroutine:
        raise TypeError(
            "The function for cache '{}' must be an async function.".format(
                c.code.co_name))

    class Ring(RingBase, Interface):
        _callable = c
        _ckey = ckey
        _expire_default = expire_default
        _interface_class = Interface

        storage = storage_instance
        _storage_impl = StorageImplementation()
        _miss_value = miss_value

        encode = staticmethod(coder.encode)
        decode = staticmethod(coder.decode)

        @functools.wraps(_callable.callable)
        def __call__(self, *args, **kwargs):
            return self.run('get_or_update', *args, **kwargs)

        @asyncio.coroutine
        def _p_execute(self, kwargs):
            result = yield from self._callable.callable(*self._preargs, **kwargs)
            return result

        @asyncio.coroutine
        def _p_get(self, key):
            value = yield from self._storage_impl.get_value(self.storage, key)
            return self.decode(value)

        @asyncio.coroutine
        def _p_set(self, key, value, expire=_expire_default):
            encoded = self.encode(value)
            yield from self._storage_impl.set_value(self.storage, key, encoded, expire)

        @asyncio.coroutine
        def _p_delete(self, key):
            yield from self._storage_impl.del_value(self.storage, key)

        @asyncio.coroutine
        def _p_touch(self, key, expire=expire_default):
            yield from self._storage_impl.touch_value(self.storage, key, expire)

    return Ring


class CacheInterface(fbase.BaseInterface):

    @asyncio.coroutine
    def _get(self, **kwargs):
        key = self._key(**kwargs)
        try:
            result = yield from self._p_get(key)
        except fbase.NotFound:
            result = self._miss_value
        return result

    @asyncio.coroutine
    def _update(self, **kwargs):
        key = self._key(**kwargs)
        result = yield from self._p_execute(kwargs)
        yield from self._p_set(key, result, self._expire_default)
        return result

    @asyncio.coroutine
    def _get_or_update(self, **kwargs):
        key = self._key(**kwargs)
        try:
            result = yield from self._p_get(key)
        except fbase.NotFound:
            result = yield from self._p_execute(kwargs)
            yield from self._p_set(key, result, self._expire_default)
        return result

    @asyncio.coroutine
    def _set(self, value, **kwargs):
        key = self._key(**kwargs)
        yield from self._p_set(key, value, self._expire_default)
    _set._function_args_count = 1

    @asyncio.coroutine
    def _delete(self, **kwargs):
        key = self._key(**kwargs)
        yield from self._p_delete(key)

    @asyncio.coroutine
    def _touch(self, **kwargs):
        key = self._key(**kwargs)
        yield from self._p_touch(key)


class DictImpl(fbase.StorageImplementation):

    now = time.time

    @asyncio.coroutine
    def get_value(self, obj, key):
        _now = self.now()
        try:
            expired_time, value = obj[key]
        except KeyError:
            raise fbase.NotFound from KeyError
        if expired_time is not None and expired_time < _now:
            raise fbase.NotFound
        return value

    @asyncio.coroutine
    def set_value(self, obj, key, value, expire):
        _now = self.now()

        if expire is None:
            expired_time = None
        else:
            expired_time = _now + expire
        obj[key] = expired_time, value

    @asyncio.coroutine
    def del_value(self, obj, key):
        try:
            del obj[key]
        except KeyError:
            pass

    @asyncio.coroutine
    def touch_value(self, obj, key, expire):
        _now = self.now()

        try:
            expired_time, value = obj[key]
        except KeyError:
            return
        if expire is None:
            expired_time = None
        else:
            expired_time = _now + expire
        obj[key] = expired_time, value


class AiomcacheImpl(fbase.StorageImplementation):
    @asyncio.coroutine
    def get_value(self, client, key):
        value = yield from client.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, client, key, value, expire):
        return client.set(key, value, expire)

    def del_value(self, client, key):
        return client.delete(key)

    def touch_value(self, client, key, expire):
        return client.touch(key, expire)


class AioredisImpl(fbase.StorageImplementation):
    @asyncio.coroutine
    def get_value(self, pool, key):
        value = yield from pool.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    @asyncio.coroutine
    def set_value(self, pool, key, value, expire):
        yield from pool.set(key, value, expire=expire)

    @asyncio.coroutine
    def del_value(self, pool, key):
        yield from pool.delete(key)

    @asyncio.coroutine
    def touch_value(self, pool, key, expire):
        yield from pool.expire(key, expire)


def dict(
        obj, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        interface=CacheInterface, storage_implementation=DictImpl):
    """Basic Python :class:`dict` based cache.

    This backend is not designed for real products, but useful by
    keeping below in mind:
    - `functools.lrucache` is the standard library for the most of local cache.
    - Expired objects will never be removed from the dict. If the function has
      unlimited input combinations, never use dict.
    - It is designed to "simulate" cache backends, not to provide an actual
      cache backend. If a caching function is a fast job, this backend even
      can drop the performance.

    Still, it doesn't mean you can't use this backend for products. Take
    advantage of it when your demands fit.

    :param dict obj: Cache storage.

    :see: :func:`ring.dict` for non-asyncio version.
    """
    return fbase.factory(
        obj, key_prefix=key_prefix, ring_factory=ring_factory,
        interface=interface, storage_implementation=storage_implementation,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)


aiodict = dict


def aiomcache(
        client, key_prefix=None, expire=0, coder=None, ignorable_keys=None,
        interface=CacheInterface, storage_implementation=AiomcacheImpl,
        key_encoding='utf-8'):
    """Memcached interface for :mod:`asyncio`.

    Expected client package is:
    - https://pypi.org/project/aiomcache/

    aiomcache expect `Memcached` client or dev package is installed on your
    machine. If you are new to Memcached, check how to install it and the python
    package on your platform.

    .. _Memcache: http://memcached.org/

    :param aiomcache.Client client: aiomcache client object.
    :param object key_refactor: The default key refactor may hash the cache key when
        it doesn't meet memcached key restriction.

    :see: :func:`ring.memcache` for non-asyncio version.
    """
    from ring._memcache import key_refactor

    return fbase.factory(
        client, key_prefix=key_prefix, ring_factory=ring_factory,
        interface=interface, storage_implementation=storage_implementation,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys,
        key_encoding=key_encoding,
        key_refactor=key_refactor)


def aioredis(
        pool, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        interface=CacheInterface, storage_implementation=AioredisImpl):
    """Redis interface for :mod:`asyncio`.

    Expected client package is:
    - https://pypi.org/project/aioredis/

    aioredis expect `Redis` client or dev package is installed on your
    machine. If you are new to Memcached, check how to install it and the python
    package on your platform.

    Note that aioredis>=1.0.0 only supported.

    .. _Redis: http://redis.io/

    :param object client: aioredis client or pool object.

    :see: :func:`ring.redis` for non-asyncio version.
    """
    return fbase.factory(
        pool, key_prefix=key_prefix, ring_factory=ring_factory,
        interface=interface, storage_implementation=storage_implementation,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)
