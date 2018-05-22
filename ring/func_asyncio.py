""":mod:`ring.func_asyncio`
is a collection of :mod:`asyncio` factory functions.
"""
from typing import Optional, Any
import asyncio
import inspect
import time
from . import func_base as fbase

__all__ = ('dict', 'aiodict', 'aiomcache', 'aioredis', )

inspect_iscoroutinefunction = getattr(
    inspect, 'iscoroutinefunction', lambda f: False)


def factory_doctor(wire_frame, ring_class) -> None:
    cwrapper = ring_class.cwrapper
    if not cwrapper.is_coroutine:
        raise TypeError(
            "The function for cache '{}' must be an async function.".format(
                cwrapper.code.co_name))


class CommonMixinStorage(fbase.BaseStorage):  # Working only as mixin
    """General :mod:`asyncio` storage root for BaseStorageMixin."""

    @asyncio.coroutine
    def get(self, key):
        value = yield from self.get_value(key)
        return self.ring.coder.decode(value)

    @asyncio.coroutine
    def set(self, key, value, expire=...):
        if expire is ...:
            expire = self.ring.expire_default
        encoded = self.ring.coder.encode(value)
        result = yield from self.set_value(key, encoded, expire)
        return result

    @asyncio.coroutine
    def delete(self, key):
        result = yield from self.delete_value(key)
        return result

    @asyncio.coroutine
    def touch(self, key, expire=...):
        if expire is ...:
            expire = self.ring.expire_default
        result = yield from self.touch_value(key, expire)
        return result


class CacheUserInterface(fbase.BaseUserInterface):

    @asyncio.coroutine
    def get(self, **kwargs):
        key = self.key(**kwargs)
        try:
            result = yield from self.ring.storage.get(key)
        except fbase.NotFound:
            result = self.ring.miss_value
        return result
    get.__annotations_override__ = {
        'return':
            lambda a: Optional[a['return']] if 'return' in a else Optional[Any],
    }

    @asyncio.coroutine
    def update(self, **kwargs):
        key = self.key(**kwargs)
        result = yield from self.execute(**kwargs)
        yield from self.ring.storage.set(key, result)
        return result

    @asyncio.coroutine
    def get_or_update(self, **kwargs):
        key = self.key(**kwargs)
        try:
            result = yield from self.ring.storage.get(key)
        except fbase.NotFound:
            result = yield from self.execute(**kwargs)
            yield from self.ring.storage.set(key, result)
        return result

    @asyncio.coroutine
    def set(self, _value, **kwargs):
        key = self.key(**kwargs)
        yield from self.ring.storage.set(key, _value)
    set._function_args_count = 1
    set.__annotations_override__ = {
        'return': None,
    }

    @asyncio.coroutine
    def delete(self, **kwargs):
        key = self.key(**kwargs)
        yield from self.ring.storage.delete(key)
    delete.__annotations_override__ = {
        'return': None,
    }

    @asyncio.coroutine
    def touch(self, **kwargs):
        key = self.key(**kwargs)
        yield from self.ring.storage.touch(key)
    touch.__annotations_override__ = {
        'return': None,
    }


class DictStorage(CommonMixinStorage, fbase.StorageMixin):

    now = time.time

    @asyncio.coroutine
    def get_value(self, key):
        _now = self.now()
        try:
            expired_time, value = self.backend[key]
        except KeyError:
            raise fbase.NotFound from KeyError
        if expired_time is not None and expired_time < _now:
            raise fbase.NotFound
        return value

    @asyncio.coroutine
    def set_value(self, key, value, expire):
        _now = self.now()

        if expire is None:
            expired_time = None
        else:
            expired_time = _now + expire
        self.backend[key] = expired_time, value

    @asyncio.coroutine
    def delete_value(self, key):
        try:
            del self.backend[key]
        except KeyError:
            pass

    @asyncio.coroutine
    def touch_value(self, key, expire):
        _now = self.now()

        try:
            expired_time, value = self.backend[key]
        except KeyError:
            return
        if expire is None:
            expired_time = None
        else:
            expired_time = _now + expire
        self.backend[key] = expired_time, value


class AiomcacheStorage(CommonMixinStorage, fbase.StorageMixin):
    @asyncio.coroutine
    def get_value(self, key):
        value = yield from self.backend.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, key, value, expire):
        return self.backend.set(key, value, expire)

    def delete_value(self, key):
        return self.backend.delete(key)

    def touch_value(self, key, expire):
        return self.backend.touch(key, expire)


class AioredisStorage(CommonMixinStorage, fbase.StorageMixin):
    @asyncio.coroutine
    def get_value(self, key):
        value = yield from self.backend.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, key, value, expire):
        return self.backend.set(key, value, expire=expire)

    def delete_value(self, key):
        return self.backend.delete(key)

    def touch_value(self, key, expire):
        return self.backend.expire(key, expire)


def dict(
        obj, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        user_interface=CacheUserInterface, storage_class=DictStorage):
    """Basic Python :class:`dict` based cache.

    This backend is not designed for real products, but useful by keeping
    below in mind:

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
        obj, key_prefix=key_prefix, on_manufactured=factory_doctor,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)


#: alias of `dict`
aiodict = dict


def aiomcache(
        client, key_prefix=None, expire=0, coder=None, ignorable_keys=None,
        user_interface=CacheUserInterface, storage_class=AiomcacheStorage,
        key_encoding='utf-8'):
    """Memcached_ interface for :mod:`asyncio`.

    Expected client package is:

    - https://pypi.org/project/aiomcache/

    aiomcache expect `Memcached` client or dev package is installed on your
    machine. If you are new to Memcached, check how to install it and the python
    package on your platform.

    :param aiomcache.Client client: aiomcache client object.
    :param object key_refactor: The default key refactor may hash the cache key
        when it doesn't meet memcached key restriction.

    :see: :func:`ring.memcache` for non-asyncio version.

    .. _Memcache: http://memcached.org/
    """
    from ring._memcache import key_refactor

    return fbase.factory(
        client, key_prefix=key_prefix, on_manufactured=factory_doctor,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys,
        key_encoding=key_encoding,
        key_refactor=key_refactor)


def aioredis(
        pool, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        user_interface=CacheUserInterface, storage_class=AioredisStorage):
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
        pool, key_prefix=key_prefix, on_manufactured=factory_doctor,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)
