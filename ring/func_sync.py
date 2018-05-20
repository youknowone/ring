""":mod:`ring.func_sync`
is a collection of factory functions.
"""
import time
import re
import hashlib
from ring import func_base as fbase

__all__ = ('dict', 'memcache', 'redis_py', 'redis', 'disk', 'arcus')


def ring_class_factory(cwrapper):

    class Ring(object):
        # primary primitive methods

        def execute(self, kwargs):
            result = self.cwrapper.callable(
                *self.wire._preargs, **kwargs)
            return result

        def storage_get(self, key):
            value = self.storage_impl.get_value(
                self.storage, key)
            return self.coder.decode(value)

        def storage_set(self, key, value, expire=Ellipsis):
            if expire is Ellipsis:
                expire = self.expire_default
            encoded = self.coder.encode(value)
            result = self.storage_impl.set_value(
                self.storage, key, encoded, expire)
            return result

        def storage_delete(self, key):
            result = self.storage_impl.del_value(
                self.storage, key)
            return result

        def storage_touch(self, key, expire=Ellipsis):
            if expire is Ellipsis:
                expire = self.expire_default
            result = self.storage_impl.touch_value(
                self.storage, key, expire)
            return result

    fbase.Ring.register(Ring)

    return Ring


class CacheInterface(fbase.BaseInterface):

    def get(self, **kwargs):
        key = self.key(**kwargs)
        try:
            result = self.ring.storage_get(key)
        except fbase.NotFound:
            result = self.ring.miss_value
        return result

    def update(self, **kwargs):
        key = self.key(**kwargs)
        result = self.ring.execute(kwargs)
        self.ring.storage_set(key, result)
        return result

    def get_or_update(self, **kwargs):
        key = self.key(**kwargs)
        try:
            result = self.ring.storage_get(key)
        except fbase.NotFound:
            result = self.ring.execute(kwargs)
            self.ring.storage_set(key, result)
        return result

    def set(self, value, **kwargs):
        key = self.key(**kwargs)
        self.ring.storage_set(key, value)
    set._function_args_count = 1

    def delete(self, **kwargs):
        key = self.key(**kwargs)
        self.ring.storage_delete(key)

    def touch(self, **kwargs):
        key = self.key(**kwargs)
        self.ring.storage_touch(key)


class DictImpl(fbase.StorageImplementation):

    now = time.time

    def get_value(self, obj, key):
        _now = self.now()
        try:
            expired_time, value = obj[key]
        except KeyError:
            raise fbase.NotFound
        if expired_time is not None and expired_time < _now:
            raise fbase.NotFound
        return value

    def set_value(self, obj, key, value, expire):
        _now = self.now()
        if expire is None:
            expired_time = None
        else:
            expired_time = _now + expire
        obj[key] = expired_time, value

    def del_value(self, obj, key):
        try:
            del obj[key]
        except KeyError:
            pass

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


class DiskImpl(fbase.StorageImplementation):
    def get_value(self, client, key):
        value = client.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, client, key, value, expire):
        client.set(key, value, expire)

    def del_value(self, client, key):
        client.delete(key)


class MemcacheImpl(fbase.StorageImplementation):
    def get_value(self, client, key):
        value = client.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, client, key, value, expire):
        client.set(key, value, expire)

    def del_value(self, client, key):
        client.delete(key)

    def touch_value(self, client, key, expire):
        client.touch(key, expire)


class RedisImplementation(fbase.StorageImplementation):
    def get_value(self, client, key):
        value = client.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, client, key, value, expire):
        client.set(key, value, expire)

    def del_value(self, client, key):
        client.delete(key)

    def touch_value(self, client, key, expire):
        if expire is None:
            raise TypeError("'touch' is requested for persistant cache")
        client.expire(key, expire)


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

    :param dict obj: Cache storage. Any :class:`dict` compatible object.

    :see: :func:`ring.aiodict` for :mod:`asyncio` version.
    """
    return fbase.factory(
        obj, key_prefix=key_prefix, ring_class_factory=ring_class_factory,
        interface=interface, storage_implementation=storage_implementation,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)


def memcache(
        client, key_prefix=None, expire=0, coder=None, ignorable_keys=None,
        interface=CacheInterface, storage_implementation=MemcacheImpl):
    """Common Memcached_ interface.

    This backend is common interface for various memcached client libraries
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

    Examples of expected client for each memcached packages:

    - pymemcache: ``pymemcache.client.Client(('127.0.0.1', 11211))``
    - python-memcached or python3-memcached:
      ``memcache.Client(["127.0.0.1:11211"])``
    - pylibmc: ``pylibmc.Client(['127.0.0.1'])``

    .. _Memcached: http://memcached.org/

    :param object client: Memcached client object. See above for details.
    :param object key_refactor: The default key refactor may hash the cache
        key when it doesn't meet memcached key restriction.

    :note: `touch` feature availability depends on memcached library.
    :see: :func:`ring.aiomcache` for :mod:`asyncio` version.
    """
    from ring._memcache import key_refactor
    miss_value = None

    return fbase.factory(
        client, key_prefix=key_prefix, ring_class_factory=ring_class_factory,
        interface=interface, storage_implementation=storage_implementation,
        miss_value=miss_value, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys,
        key_refactor=key_refactor)


def redis_py(
        client, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        interface=CacheInterface, storage_implementation=RedisImplementation):
    """Redis_ interface.

    This backend depends on `redis-py`_.

    The `redis` package expects Redis client or dev package is installed on
    your machine. If you are new to Redis, check how to install Redis and the
    Python package on your platform.

    Note that :class:`redis.StrictRedis` is expected, which is different to
    :class:`redis.Redis`.

    :param redis.StrictRedis client: Redis client object.

    :see: :func:`ring.aioredis` for :mod:`asyncio` version.
    :see: Redis_ for Redis documentation.

    .. _Redis: http://redis.io/
    .. _redis-py: https://pypi.org/project/redis/
    """
    return fbase.factory(
        client, key_prefix=key_prefix, ring_class_factory=ring_class_factory,
        interface=interface, storage_implementation=storage_implementation,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)


redis = redis_py  #: Alias for redis_py for now.


def disk(
        obj, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        interface=CacheInterface, storage_implementation=DiskImpl):
    """diskcache_ interface

    .. _diskcache: https://pypi.org/project/diskcache/

    :param diskcache.Cache obj: diskcache Cache object.
    """
    return fbase.factory(
        obj, key_prefix=key_prefix, ring_class_factory=ring_class_factory,
        interface=interface, storage_implementation=storage_implementation,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)


def arcus(
        client, key_prefix=None, expire=0, coder=None, ignorable_keys=None,
        interface=CacheInterface):

    class Impl(fbase.Storage):
        def get_value(self, client, key):
            value = client.get(key).get_result()
            if value is None:
                raise fbase.NotFound
            return value

        def set_value(self, client, key, value):
            client.set(key, value, expire)

        def del_value(self, client, key):
            client.delete(key)

        def touch_value(self, client, key, expire):
            client.touch(key, expire)

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
        client, key_prefix=key_prefix, ring_class_factory=ring_class_factory,
        interface=interface, storage_implementation=Impl,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys,
        key_refactor=key_refactor)
