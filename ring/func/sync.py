""":mod:`ring.func.sync` --- collection of synchronous factory functions.
=========================================================================

This module includes building blocks and storage implementations of **Ring**
factories.
"""
from typing import Any, Optional, List
import time
import re
import hashlib

from . import base as fbase, lru_cache as lru_mod

__all__ = (
    'lru', 'dict', 'memcache', 'redis_py', 'redis_py_hash', 'shelve',
    'diskcache')


class CacheUserInterface(fbase.BaseUserInterface):
    """General cache user interface provider.

    :see: :class:`ring.func.base.BaseUserInterface` for class and methods
        details.
    """

    @fbase.interface_attrs(
        transform_args=fbase.transform_kwargs_only,
        return_annotation=lambda a: Optional[a.get('return', Any)])
    def get(self, wire, **kwargs):
        key = self.key(wire, **kwargs)
        try:
            result = self.rope.storage.get(key)
        except fbase.NotFound:
            result = self.rope.miss_value
        return result

    @fbase.interface_attrs(transform_args=fbase.transform_kwargs_only)
    def update(self, wire, **kwargs):
        key = wire.key(**kwargs)
        result = wire.execute(**kwargs)
        self.rope.storage.set(key, result)
        return result

    @fbase.interface_attrs(transform_args=fbase.transform_kwargs_only)
    def get_or_update(self, wire, **kwargs):
        key = self.key(wire, **kwargs)
        try:
            result = self.rope.storage.get(key)
        except fbase.NotFound:
            result = self.execute(wire, **kwargs)
            self.rope.storage.set(key, result)
        return result

    @fbase.interface_attrs(
        transform_args=(fbase.transform_kwargs_only, {'prefix_count': 1}),
        return_annotation=None)
    def set(self, wire, _value, **kwargs):
        key = self.key(wire, **kwargs)
        self.rope.storage.set(key, _value)

    @fbase.interface_attrs(
        transform_args=fbase.transform_kwargs_only, return_annotation=None)
    def delete(self, wire, **kwargs):
        key = self.key(wire, **kwargs)
        self.rope.storage.delete(key)

    @fbase.interface_attrs(
        transform_args=fbase.transform_kwargs_only, return_annotation=bool)
    def has(self, wire, **kwargs):
        key = self.key(wire, **kwargs)
        return self.rope.storage.has(key)

    @fbase.interface_attrs(
        transform_args=fbase.transform_kwargs_only, return_annotation=None)
    def touch(self, wire, **kwargs):
        key = self.key(wire, **kwargs)
        self.rope.storage.touch(key)


class BulkInterfaceMixin(fbase.AbstractBulkUserInterfaceMixin):
    """Bulk access interface mixin.

    Any corresponding storage class must be a subclass of
    :class:`ring.func.sync.BulkStorageMixin`.
    """

    @fbase.interface_attrs(
        return_annotation=lambda a: List[a.get('return', Any)])
    def execute_many(self, wire, *args_list):
        values = [fbase.execute_bulk_item(wire, args) for args in args_list]
        return values

    @fbase.interface_attrs(
        return_annotation=lambda a: List[Optional[a.get('return', Any)]])
    def get_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        results = self.rope.storage.get_many(
            keys, miss_value=self.rope.miss_value)
        return results

    @fbase.interface_attrs(
        return_annotation=lambda a: List[a.get('return', Any)])
    def update_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        values = self.execute_many(wire, *args_list)
        self.rope.storage.set_many(keys, values)
        return values

    @fbase.interface_attrs(
        return_annotation=lambda a: List[a.get('return', Any)])
    def get_or_update_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        miss_value = object()
        results = self.rope.storage.get_many(keys, miss_value=miss_value)

        miss_indices = []
        for i, akr in enumerate(zip(args_list, keys, results)):
            args, key, result = akr
            if result is not miss_value:
                continue
            miss_indices.append(i)

        new_results = [
            fbase.execute_bulk_item(wire, args_list[i]) for i in miss_indices]
        new_keys = [keys[i] for i in miss_indices]
        self.rope.storage.set_many(new_keys, new_results)

        for new_i, old_i in enumerate(miss_indices):
            results[old_i] = new_results[new_i]
        return results

    @fbase.interface_attrs(return_annotation=None)
    def set_many(self, wire, args_list, value_list):
        keys = self.key_many(wire, *args_list)
        self.rope.storage.set_many(keys, value_list)

    @fbase.interface_attrs(return_annotation=None)
    def delete_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        self.rope.storage.delete_many(keys)

    @fbase.interface_attrs(return_annotation=None)
    def has_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        self.rope.storage.has_many(keys)

    @fbase.interface_attrs(return_annotation=None)
    def touch_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        self.rope.storage.touch_many(keys)


class BulkStorageMixin(object):

    def get_many(self, keys, miss_value):
        values = self.get_many_values(keys)
        results = [
            self.rope.decode(v) if v is not fbase.NotFound else miss_value  # noqa
            for v in values]
        return results

    def set_many(self, keys, values, expire=Ellipsis):
        if expire is Ellipsis:
            expire = self.rope.expire_default
        self.set_many_values(
            keys, [self.rope.encode(v) for v in values], expire)

    def delete_many(self, keys):
        self.delete_many_values(keys)

    def has_many(self, keys):
        return self.has_many_values(keys)

    def touch_many(self, keys, expire=Ellipsis):
        if expire is Ellipsis:
            expire = self.rope.expire_default
        self.touch_many_values(keys, expire)


class LruStorage(fbase.CommonMixinStorage, fbase.StorageMixin):

    def get_value(self, key):
        value = self.backend.get(key)
        if value is lru_mod.SENTINEL:
            raise fbase.NotFound
        return value

    def has_value(self, key):
        return self.backend.has(key)

    def set_value(self, key, value, expire):
        self.backend.set(key, value)

    def delete_value(self, key):
        try:
            self.backend.delete(key)
        except KeyError:
            pass

    def touch_value(self, key, expire):
        try:
            self.backend.touch(key)
        except KeyError:
            pass


class ExpirableDictStorage(fbase.CommonMixinStorage, fbase.StorageMixin):

    now = time.time

    def get_value(self, key):
        _now = self.now()
        try:
            expired_time, value = self.backend[key]
        except KeyError:
            raise fbase.NotFound
        if expired_time is not None and expired_time < _now:
            raise fbase.NotFound
        return value

    def set_value(self, key, value, expire):
        _now = self.now()
        if expire is None:
            expired_time = None
        else:
            expired_time = _now + expire
        self.backend[key] = expired_time, value

    def delete_value(self, key):
        try:
            del self.backend[key]
        except KeyError:
            pass

    def has_value(self, key):
        return key in self.backend

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


class PersistentDictStorage(fbase.CommonMixinStorage, fbase.StorageMixin):

    def get_value(self, key):
        try:
            value = self.backend[key]
        except KeyError:
            raise fbase.NotFound
        return value

    def set_value(self, key, value, expire):
        self.backend[key] = value

    def delete_value(self, key):
        try:
            del self.backend[key]
        except KeyError:
            pass

    def has_value(self, key):
        return key in self.backend


class ShelveStorage(PersistentDictStorage):

    def set_value(self, key, value, expire):
        super(ShelveStorage, self).set_value(key, value, expire)
        self.backend.sync()

    def delete_value(self, key):
        super(ShelveStorage, self).delete_value(key)
        self.backend.sync()


class MemcacheStorage(
        fbase.CommonMixinStorage, fbase.StorageMixin, BulkStorageMixin):

    def get_value(self, key):
        value = self.backend.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, key, value, expire):
        self.backend.set(key, value, expire)

    def delete_value(self, key):
        self.backend.delete(key)

    def touch_value(self, key, expire):
        self.backend.touch(key, expire)

    def get_many_values(self, keys):
        values = self.backend.get_multi(keys)
        return [values.get(k, fbase.NotFound) for k in keys]

    def set_many_values(self, keys, values, expire):
        self.backend.set_multi({k: v for k, v in zip(keys, values)}, expire)

    def delete_many_values(self, keys):
        return self.backend.delete_multi(keys)


class RedisStorage(
        fbase.CommonMixinStorage, fbase.StorageMixin, BulkStorageMixin):

    def get_value(self, key):
        value = self.backend.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, key, value, expire):
        self.backend.set(key, value, expire)

    def delete_value(self, key):
        self.backend.delete(key)

    def has_value(self, key):
        return bool(self.backend.exists(key))

    def touch_value(self, key, expire):
        if expire is None:
            raise TypeError("'touch' is requested for persistent cache")
        self.backend.expire(key, expire)

    def get_many_values(self, keys):
        values = self.backend.mget(keys)
        return [v if v is not None else fbase.NotFound for v in values]

    def set_many_values(self, keys, values, expire):
        self.backend.mset({k: v for k, v in zip(keys, values)})
        if expire is not None:
            for key in keys:
                self.backend.expire(key, expire)


class RedisHashStorage(RedisStorage):

    def __init__(self, rope, backend):
        storage_backend = backend[0]
        self.hash_key = backend[1]
        super(RedisHashStorage, self).__init__(rope, storage_backend)

    def get_value(self, key):
        value = self.backend.hget(self.hash_key, key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, key, value, expire):
        self.backend.hset(self.hash_key, key, value)

    def delete_value(self, key):
        self.backend.hdel(self.hash_key, key)

    def has_value(self, key):
        return self.backend.hexists(self.hash_key, key)

    def get_many_values(self, keys):
        values = self.backend.hmget(self.hash_key, keys)
        return [v if v is not None else fbase.NotFound for v in values]

    def set_many_values(self, keys, values, expire):
        self.backend.hmset(self.hash_key, {k: v for k, v in zip(keys, values)})


class DiskCacheStorage(fbase.CommonMixinStorage, fbase.StorageMixin):

    def get_value(self, key):
        value = self.backend.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, key, value, expire):
        self.backend.set(key, value, expire)

    def delete_value(self, key):
        self.backend.delete(key)


def lru(
        lru=None, key_prefix=None, coder=None, ignorable_keys=None,
        user_interface=CacheUserInterface, storage_class=LruStorage,
        maxsize=128, **kwargs):
    """LRU(Least-Recently-Used) cache interface.

    Because the lru backend is following the basic manner of
    :func:`functools.lru_cache`, see the document for LRU cache details.

        >>> @ring.lru(maxsize=128)
        >>> def f(...):
        ...     ...

    The above is very similar to below:

        >>> @functools.lru_cache(maxsize=128, typed=False)
        >>> def f(...):
        ...     ...

    Note that **ring** basically supports key consistency and manual
    operation features, unlike :func:`functools.lru_cache`.

    :param ring.func.lru_cache.LruCache lru: Cache storage. If the default
        value :data:`None` is given, a new `LruCache`
        object will be created. (Recommended)
    :param int maxsize: The maximum size of the cache storage.

    :see: :func:`functools.lru_cache` for LRU cache basics.
    :see: :func:`ring.func.sync.CacheUserInterface` for sub-functions.
    """
    expire = None
    if lru is None:
        lru = lru_mod.LruCache(maxsize)
        if key_prefix is None:
            key_prefix = ''

    return fbase.factory(
        lru, key_prefix=key_prefix, on_manufactured=None,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys,
        **kwargs)


def dict(
        obj, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        user_interface=CacheUserInterface, storage_class=None,
        **kwargs):
    """Basic Python :class:`dict` based cache.

    This backend is not designed for real products. Please carefully read the
    next details to check it fits your demands.

    - :func:`ring.lru` and :func:`functools.lru_cache` are the standard way
      for the most of local cache.
    - Expired objects will never be removed from the dict. If the function has
      unlimited input combinations, never use dict.
    - It is designed to "simulate" cache backends, not to provide an actual
      cache backend. If a caching function is a fast job, this backend even
      can drop the performance.

    :param dict obj: Cache storage. Any :class:`dict` compatible object.

    :see: :func:`ring.func.sync.CacheUserInterface` for sub-functions.
    :see: :func:`ring.dict` for :mod:`asyncio` version.
    """
    if storage_class is None:
        if expire is None:
            storage_class = PersistentDictStorage
        else:
            storage_class = ExpirableDictStorage

    return fbase.factory(
        obj, key_prefix=key_prefix, on_manufactured=None,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys,
        **kwargs)


def shelve(
        shelf, key_prefix=None, coder=None, ignorable_keys=None,
        user_interface=CacheUserInterface, storage_class=ShelveStorage,
        **kwargs):
    """Python :mod:`shelve` based cache.

    :param shelve.Shelf shelf: A shelf storage. See :mod:`shelve` to create
        a shelf.

        >>> shelf = shelve.open('shelve')
        >>> @ring.shelve(shelf, ...)
        ...     ...

    :see: :mod:`shelve` for the backend.
    :see: :func:`ring.func.sync.CacheUserInterface` for sub-functions.
    """
    expire = None
    return fbase.factory(
        shelf, key_prefix=key_prefix, on_manufactured=None,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys,
        **kwargs)


def memcache(
        client, key_prefix=None, expire=0, coder=None, ignorable_keys=None,
        user_interface=(CacheUserInterface, BulkInterfaceMixin),
        storage_class=MemcacheStorage,
        **kwargs):
    """Common Memcached_ interface.

    This backend is shared interface for various memcached client libraries
    below:

    - https://pypi.org/project/python-memcached/
    - https://pypi.org/project/python3-memcached/
    - https://pypi.org/project/pylibmc/
    - https://pypi.org/project/pymemcache/

    Most of them expect `Memcached` client or dev package is installed on your
    machine. If you are new to Memcached, check how to install it and the
    python package on your platform.

    The expected types for input and output are always :class:`bytes` for
    `None` coder, but you may use different types depending on client
    libraries. Ring doesn't guarantee current/future behavior except for
    :class:`bytes`.

    :note: `touch` feature availability depends on Memcached library.

    .. _Memcached: http://memcached.org/

    :param object client: Memcached client object. See below for details.

        - pymemcache: :class:`pymemcache.client.Client`

        >>> client = pymemcache.client.Client(('127.0.0.1', 11211))
        >>> @ring.memcache(client, ...)
        ...     ...

        - python-memcached or python3-memcached: :class:`memcache.Client`

        >>> client = memcache.Client(["127.0.0.1:11211"])
        >>> @ring.memcache(client, ...)
        ...     ...

        - pylibmc: :class:`pylibmc.Client`

        >>> client = pylibmc.Client(['127.0.0.1'])
        >>> @ring.memcache(client, ...)
        ...     ...

    :param object key_refactor: The default key refactor may hash the cache
        key when it doesn't meet Memcached key restriction.

    :see: :func:`ring.func.sync.CacheUserInterface` for single access
        sub-functions.
    :see: :func:`ring.func.sync.BulkInterfaceMixin` for bulk access
        sub-functions.

    :see: :func:`ring.aiomcache` for :mod:`asyncio` version.
    """
    from ring._memcache import key_refactor
    miss_value = None

    return fbase.factory(
        client, key_prefix=key_prefix, on_manufactured=None,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=miss_value, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys, key_refactor=key_refactor,
        **kwargs)


def redis_py(
        client, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        user_interface=(CacheUserInterface, BulkInterfaceMixin),
        storage_class=RedisStorage,
        **kwargs):
    """Redis_ interface.

    This backend depends on `redis-py`_.

    The `redis` package expects Redis client or dev package is installed on
    your machine. If you are new to Redis, check how to install Redis and the
    Python package on your platform.

    Note that :class:`redis.StrictRedis` is expected, which is different from
    :class:`redis.Redis`.

    :param redis.StrictRedis client: Redis client object. See
        :class:`redis.StrictRedis`

        >>> client = redis.StrictRedis()
        >>> @ring.redis(client, ...)
        ...     ...

    :see: :func:`ring.func.sync.CacheUserInterface` for single access
        sub-functions.
    :see: :func:`ring.func.sync.BulkInterfaceMixin` for bulk access
        sub-functions.

    :see: :func:`ring.aioredis` for :mod:`asyncio` version.
    :see: Redis_ for Redis documentation.

    .. _Redis: http://redis.io/
    .. _redis-py: https://pypi.org/project/redis/
    """
    return fbase.factory(
        client, key_prefix=key_prefix, on_manufactured=None,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys,
        **kwargs)


def redis_py_hash(
        client, hash_key=None, key_prefix=None, coder=None, ignorable_keys=None,
        user_interface=(CacheUserInterface, BulkInterfaceMixin),
        storage_class=RedisHashStorage,
        **kwargs):
    """
    This backend depends on `redis-py`_.

    This implements HASH commands in Redis.

    Note that :class:`redis.StrictRedis` is expected, which is different from
    :class:`redis.Redis`.

    :param redis.StrictRedis client: Redis client object. See
        :class:`redis.StrictRedis`

        >>> client = redis.StrictRedis()
        >>> @ring.redis_hash(client, ...)
        ...     ...

    :see: :func:`ring.func.sync.CacheUserInterface` for single access
        sub-functions.
    :see: :func:`ring.func.sync.BulkInterfaceMixin` for bulk access
        sub-functions.

    :see: Redis_ for Redis documentation.

    .. _Redis: http://redis.io/
    .. _Redis HASH commands: https://redis.io/commands#hash
    .. _redis-py: https://pypi.org/project/redis/
    """
    expire = None
    return fbase.factory(
        (client, hash_key), key_prefix=key_prefix, on_manufactured=None,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys,
        **kwargs)


def diskcache(
        obj, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        user_interface=CacheUserInterface, storage_class=DiskCacheStorage,
        **kwargs):
    """diskcache_ interface.

    .. _diskcache: https://pypi.org/project/diskcache/

    :param diskcache.Cache obj: diskcache Cache object. See
        :class:`diskcache.Cache`.

        >>> storage = diskcache.Cache('cachedir')
        >>> @ring.disk(storage, ...)
        ...     ...

    :see: :func:`ring.func.sync.CacheUserInterface` for sub-functions.
    """
    return fbase.factory(
        obj, key_prefix=key_prefix, on_manufactured=None,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys,
        **kwargs)


def arcus(
        client, key_prefix=None, expire=0, coder=None, ignorable_keys=None,
        default_action='get_or_update',
        user_interface=CacheUserInterface,
        **kwargs):  # pragma: no cover
    """Arcus support. deprecated."""
    class Storage(fbase.CommonMixinStorage, fbase.StorageMixin):
        def get_value(self, key):
            value = self.backend.get(key).get_result()
            if value is None:
                raise fbase.NotFound
            return value

        def set_value(self, key, value, expire):
            self.backend.set(key, value, expire)

        def delete_value(self, key):
            self.backend.delete(key)

        def touch_value(self, key, expire):
            self.backend.touch(key, expire)

    rule = re.compile(r'[!-~]+')

    def key_refactor(key):
        if len(key) < 250 and rule.match(key).group(0) == key:
            return key
        try:
            hashed = hashlib.sha1(key).hexdigest()
        except TypeError:
            # FIXME: ensure key is bytes before key_refactor
            key = key.encode('utf-8')
            hashed = hashlib.sha1(key).hexdigest()
        return 'ring-sha1:' + hashed

    return fbase.factory(
        client, key_prefix=key_prefix, on_manufactured=None,
        user_interface=user_interface, storage_class=Storage,
        default_action=default_action,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys,
        key_refactor=key_refactor,
        **kwargs)
