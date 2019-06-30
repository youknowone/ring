""":mod:`ring.func.asyncio` --- collection of :mod:`asyncio` factory functions.
===============================================================================

This module includes building blocks and storage implementations of **Ring**
factories for :mod:`asyncio`.
"""
from typing import Any, Optional, List
import asyncio
import inspect
import itertools
from . import base as fbase, sync as fsync

__all__ = ('aiomcache', 'aioredis', )

inspect_iscoroutinefunction = getattr(
    inspect, 'iscoroutinefunction', lambda f: False)


class SingletonCoroutineProxy(object):

    def __init__(self, awaitable):
        if not asyncio.iscoroutine(awaitable):
            raise TypeError(
                "StorageProxy requires an awaitable object but '{}' found"
                .format(type(awaitable)))
        self.awaitable = awaitable
        self.singleton = None

    def __iter__(self):
        if self.singleton is None:
            if hasattr(self.awaitable, '__await__'):
                awaitable = self.awaitable.__await__()
            else:
                awaitable = self.awaitable
            self.singleton = yield from awaitable
        return self.singleton

    __await__ = __iter__


class NonAsyncioFactoryProxyBase(fbase.FactoryProxyBase):

    def __init__(self, *args, **kwargs):
        self.force_asyncio = kwargs.pop('force_asyncio', False)
        super().__init__(*args, **kwargs)

    def __call__(self, func):
        is_coroutine = fbase.asyncio_binary_classifier(func) == 1
        if is_coroutine and not self.force_asyncio:
            raise TypeError(
                "'{f.__name__}' function is an asyncio coroutine but the ring "
                "factory does not support asyncio. This may result in the "
                "storage operation blocking asyncio event loop which may "
                "slow down the program. To force to allow it, pass "
                "keyword parameter 'force_asyncio=True' to the ring factory.")
        return super().__call__(func)


def create_asyncio_factory_proxy(factory_table, *, support_asyncio):
    if support_asyncio:
        proxy_base = fbase.FactoryProxyBase
    else:
        proxy_base = NonAsyncioFactoryProxyBase
    classifier = fbase.asyncio_binary_classifier
    return fbase.create_factory_proxy(proxy_base, classifier, factory_table)


def convert_storage(storage_class):
    storage_bases = (fbase.CommonMixinStorage, BulkStorageMixin)
    async_storage_class = type(
        'Async' + storage_class.__name__, (storage_class,), {})

    count = 0
    for storage_base in storage_bases:
        if issubclass(storage_class, storage_base):
            count += 1
            for name in storage_base.__dict__.keys():
                async_attr = asyncio.coroutine(getattr(storage_class, name))
                setattr(async_storage_class, name, async_attr)
    if count == 0:
        raise TypeError(
            "'storage_class' is not subclassing any known storage base")

    return async_storage_class


def create_factory_from(sync_factory, _storage_class):
    """Create :mod:`asyncio` compatible factory from synchronous storage."""

    def factory(*args, **kwargs):
        if 'user_interface' not in kwargs:
            kwargs['user_interface'] = CacheUserInterface
        if 'storage_class' not in kwargs:
            kwargs['storage_class'] = convert_storage(_storage_class)
        return sync_factory(*args, **kwargs)

    return factory


def factory_doctor(wire_rope) -> None:
    callable = wire_rope.callable
    if not callable.is_coroutine:
        raise TypeError(
            "The function for cache '{}' must be an async function.".format(
                callable.code.co_name))


class CommonMixinStorage(fbase.BaseStorage):  # Working only as mixin
    """General :mod:`asyncio` storage root for BaseStorageMixin."""

    @asyncio.coroutine
    def get(self, key):
        value = yield from self.get_value(key)
        return self.rope.decode(value)

    @asyncio.coroutine
    def set(self, key, value, expire=...):
        if expire is ...:
            expire = self.rope.expire_default
        encoded = self.rope.encode(value)
        result = yield from self.set_value(key, encoded, expire)
        return result

    @asyncio.coroutine
    def delete(self, key):
        result = yield from self.delete_value(key)
        return result

    @asyncio.coroutine
    def has(self, key):
        result = yield from self.has_value(key)
        return result

    @asyncio.coroutine
    def touch(self, key, expire=...):
        if expire is ...:
            expire = self.rope.expire_default
        result = yield from self.touch_value(key, expire)
        return result


class CacheUserInterface(fbase.BaseUserInterface):
    """General cache user interface provider for :mod:`asyncio`.

    :see: :class:`ring.func.base.BaseUserInterface` for class and methods
        details.
    """

    @fbase.interface_attrs(
        transform_args=fbase.transform_kwargs_only,
        return_annotation=lambda a: Optional[a.get('return', Any)])
    @asyncio.coroutine
    def get(self, wire, **kwargs):
        key = self.key(wire, **kwargs)
        try:
            result = yield from self.rope.storage.get(key)
        except fbase.NotFound:
            result = self.rope.miss_value
        return result

    @fbase.interface_attrs(transform_args=fbase.transform_kwargs_only)
    @asyncio.coroutine
    def update(self, wire, **kwargs):
        key = self.key(wire, **kwargs)
        result = yield from self.execute(wire, **kwargs)
        yield from self.rope.storage.set(key, result)
        return result

    @fbase.interface_attrs(transform_args=fbase.transform_kwargs_only)
    @asyncio.coroutine
    def get_or_update(self, wire, **kwargs):
        key = self.key(wire, **kwargs)
        try:
            result = yield from self.rope.storage.get(key)
        except fbase.NotFound:
            result = yield from self.execute(wire, **kwargs)
            yield from self.rope.storage.set(key, result)
        return result

    @fbase.interface_attrs(
        transform_args=(fbase.transform_kwargs_only, {'prefix_count': 1}),
        return_annotation=None)
    def set(self, wire, _value, **kwargs):
        key = self.key(wire, **kwargs)
        return self.rope.storage.set(key, _value)

    @fbase.interface_attrs(
        transform_args=fbase.transform_kwargs_only, return_annotation=None)
    def delete(self, wire, **kwargs):
        key = self.key(wire, **kwargs)
        return self.rope.storage.delete(key)

    @fbase.interface_attrs(
        transform_args=fbase.transform_kwargs_only, return_annotation=bool)
    def has(self, wire, **kwargs):
        key = self.key(wire, **kwargs)
        return self.rope.storage.has(key)

    @fbase.interface_attrs(
        transform_args=fbase.transform_kwargs_only, return_annotation=None)
    def touch(self, wire, **kwargs):
        key = self.key(wire, **kwargs)
        return self.rope.storage.touch(key)


class BulkInterfaceMixin(fbase.AbstractBulkUserInterfaceMixin):
    """Bulk access interface mixin.

    Any corresponding storage class must be a subclass of
    :class:`ring.func.asyncio.BulkStorageMixin`.
    """

    @fbase.interface_attrs(
        return_annotation=lambda a: List[a.get('return', Any)])
    def execute_many(self, wire, *args_list):
        return asyncio.gather(*(
            fbase.execute_bulk_item(wire, args) for args in args_list))

    @fbase.interface_attrs(
        return_annotation=lambda a: List[Optional[a.get('return', Any)]])
    def get_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        return self.rope.storage.get_many(
            keys, miss_value=self.rope.miss_value)

    @fbase.interface_attrs(
        return_annotation=lambda a: List[a.get('return', Any)])
    @asyncio.coroutine
    def update_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        values = yield from self.execute_many(wire, *args_list)
        yield from self.rope.storage.set_many(keys, values)
        return values

    @fbase.interface_attrs(
        return_annotation=lambda a: List[a.get('return', Any)])
    @asyncio.coroutine
    def get_or_update_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        miss_value = object()
        results = yield from self.rope.storage.get_many(
            keys, miss_value=miss_value)

        miss_indices = []
        for i, akr in enumerate(zip(args_list, keys, results)):
            args, key, result = akr
            if result is not miss_value:
                continue
            miss_indices.append(i)

        new_results = yield from asyncio.gather(*(
            fbase.execute_bulk_item(wire, args_list[i]) for i in miss_indices))
        new_keys = [keys[i] for i in miss_indices]
        yield from self.rope.storage.set_many(new_keys, new_results)

        for new_i, old_i in enumerate(miss_indices):
            results[old_i] = new_results[new_i]
        return results

    @fbase.interface_attrs(return_annotation=None)
    def set_many(self, wire, args_list, value_list):
        keys = self.key_many(wire, *args_list)
        return self.rope.storage.set_many(keys, value_list)

    @fbase.interface_attrs(return_annotation=None)
    def delete_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        return self.rope.storage.delete_many(keys)

    @fbase.interface_attrs(return_annotation=None)
    def has_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        return self.rope.storage.has_many(keys)

    @fbase.interface_attrs(return_annotation=None)
    def touch_many(self, wire, *args_list):
        keys = self.key_many(wire, *args_list)
        return self.rope.storage.touch_many(keys)


class BulkStorageMixin(object):

    @asyncio.coroutine
    def get_many(self, keys, miss_value):
        """Get and return values for the given key."""
        values = yield from self.get_many_values(keys)
        results = [
            self.rope.decode(v) if v is not fbase.NotFound else miss_value  # noqa
            for v in values]
        return results

    def set_many(self, keys, values, expire=Ellipsis):
        """Set values for the given keys."""
        if expire is Ellipsis:
            expire = self.rope.expire_default
        return self.set_many_values(
            keys, [self.rope.encode(v) for v in values], expire)

    def delete_many(self, keys):
        """Delete values for the given keys."""
        return self.delete_many_values(keys)

    def has_many(self, keys):
        """Check and return existences for the given keys."""
        return self.has_many_values(keys)

    def touch_many(self, keys, expire=Ellipsis):
        """Touch values for the given keys."""
        if expire is Ellipsis:
            expire = self.rope.expire_default
        return self.touch_many_values(keys, expire)


class AiomcacheStorage(
        CommonMixinStorage, fbase.StorageMixin, BulkStorageMixin):
    """Storage implementation for :class:`aiomcache.Client`."""

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

    @asyncio.coroutine
    def get_many_values(self, keys):
        values = yield from self.backend.multi_get(*keys)
        return [v if v is not None else fbase.NotFound for v in values]

    def set_many_values(self, keys, values, expire):
        raise NotImplementedError("aiomcache doesn't support set_multi.")

    def delete_many_values(self, keys):
        raise NotImplementedError("aiomcache doesn't support delete_multi.")


class AioredisStorage(
        CommonMixinStorage, fbase.StorageMixin, BulkStorageMixin):
    """Storage implementation for :class:`aioredis.Redis`."""

    @asyncio.coroutine
    def _get_backend(self):
        backend = yield from self.backend
        return backend

    @asyncio.coroutine
    def get_value(self, key):
        backend = yield from self._get_backend()
        value = yield from backend.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    @asyncio.coroutine
    def set_value(self, key, value, expire):
        backend = yield from self._get_backend()
        result = yield from backend.set(key, value, expire=expire)
        return result

    @asyncio.coroutine
    def delete_value(self, key):
        backend = yield from self._get_backend()
        result = yield from backend.delete(key)
        return result

    @asyncio.coroutine
    def has_value(self, key):
        backend = yield from self._get_backend()
        result = yield from backend.exists(key)
        return bool(result)

    @asyncio.coroutine
    def touch_value(self, key, expire):
        if expire is None:
            raise TypeError("'touch' is requested for persistent cache")
        backend = yield from self._get_backend()
        result = yield from backend.expire(key, expire)
        return result

    @asyncio.coroutine
    def get_many_values(self, keys):
        backend = yield from self._get_backend()
        values = yield from backend.mget(*keys)
        return [v if v is not None else fbase.NotFound for v in values]

    @asyncio.coroutine
    def set_many_values(self, keys, values, expire):
        params = itertools.chain.from_iterable(zip(keys, values))
        backend = yield from self._get_backend()
        yield from backend.mset(*params)
        if expire is not None:
            asyncio.ensure_future(asyncio.gather(*(
                backend.expire(key, expire) for key in keys)))


class AioredisHashStorage(AioredisStorage):
    """Storage implementation for :class:`aioredis.Redis`."""

    def __init__(self, rope, backend):
        storage_backend = backend[0]
        self.hash_key = backend[1]
        super(AioredisHashStorage, self).__init__(rope, storage_backend)

    @asyncio.coroutine
    def get_value(self, key):
        backend = yield from self._get_backend()
        value = yield from backend.hget(self.hash_key, key)
        if value is None:
            raise fbase.NotFound
        return value

    @asyncio.coroutine
    def set_value(self, key, value, expire):
        backend = yield from self._get_backend()
        result = yield from backend.hset(self.hash_key, key, value)
        return result

    @asyncio.coroutine
    def delete_value(self, key):
        backend = yield from self._get_backend()
        result = yield from backend.hdel(self.hash_key, key)
        return result

    @asyncio.coroutine
    def has_value(self, key):
        backend = yield from self._get_backend()
        result = yield from backend.hexists(self.hash_key, key)
        return bool(result)

    @asyncio.coroutine
    def get_many_values(self, keys):
        backend = yield from self._get_backend()
        values = yield from backend.hmget(self.hash_key, *keys)
        return [v if v is not None else fbase.NotFound for v in values]

    @asyncio.coroutine
    def set_many_values(self, keys, values, expire):
        params = itertools.chain.from_iterable(zip(keys, values))
        backend = yield from self._get_backend()
        yield from backend.hmset(self.hash_key, *params)


def dict(
        obj, key_prefix=None, expire=None, coder=None,
        user_interface=CacheUserInterface, storage_class=None,
        maxsize=128, **kwargs):
    """:class:`dict` interface for :mod:`asyncio`.

    :see: :func:`ring.func.sync.dict` for common description.
    """

    if storage_class is None:
        if expire is None:
            storage_class = fsync.PersistentDictStorage
        else:
            storage_class = fsync.ExpirableDictStorage
        storage_class.maxsize = maxsize

    return fbase.factory(
        obj, key_prefix=key_prefix, on_manufactured=None,
        user_interface=user_interface,
        storage_class=convert_storage(storage_class),
        miss_value=None, expire_default=expire, coder=coder,
        **kwargs)


def aiomcache(
        client, key_prefix=None, expire=0, coder=None,
        user_interface=(CacheUserInterface, BulkInterfaceMixin),
        storage_class=AiomcacheStorage, key_encoding='utf-8',
        **kwargs):
    """Memcached_ interface for :mod:`asyncio`.

    Expected client package is aiomcache_.

    aiomcache expect `Memcached` client or dev package is installed on your
    machine. If you are new to Memcached, check how to install it and the
    python package on your platform.

    :param aiomcache.Client client: aiomcache client object. See
        :func:`aiomcache.Client`.

        >>> client = aiomcache.Client('127.0.0.1', 11211)
    :param object key_refactor: The default key refactor may hash the cache
        key when it doesn't meet Memcached key restriction.

    :see: :func:`ring.func.asyncio.CacheUserInterface` for single access
        sub-functions.
    :see: :func:`ring.func.asyncio.BulkInterfaceMixin` for bulk access
        sub-functions.

    :see: :func:`ring.func.sync.memcache` for non-asyncio version.

    .. _Memcached: http://memcached.org/
    .. _aiomcache: https://pypi.org/project/aiomcache/
    """
    from ring._memcache import key_refactor

    return fbase.factory(
        client, key_prefix=key_prefix, on_manufactured=factory_doctor,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        key_encoding=key_encoding, key_refactor=key_refactor,
        **kwargs)


def aioredis(
        redis, key_prefix=None, expire=None, coder=None,
        user_interface=(CacheUserInterface, BulkInterfaceMixin),
        storage_class=AioredisStorage,
        **kwargs):
    """Redis interface for :mod:`asyncio`.

    Expected client package is aioredis_.

    aioredis expect `Redis` client or dev package is installed on your
    machine. If you are new to Memcached, check how to install it and the
    python package on your platform.

    Note that aioredis>=1.0.0 only supported.

    .. _Redis: http://redis.io/
    .. _aioredis: https://pypi.org/project/aioredis/

    :param Union[aioredis.Redis,Callable[...aioredis.Redis]] client: aioredis
        interface object. See :func:`aioredis.create_redis` or
        :func:`aioredis.create_redis_pool`. For convenience, a coroutine
        returning one of these objects also is proper. It means next 2
        examples working almost same:

            >>> redis = await aioredis.create_redis(('127.0.0.1', 6379))
            >>> @ring.aioredis(redis)
            >>> async def by_object(...):
            >>>     ...

            >>> redis_coroutine = aioredis.create_redis(('127.0.0.1', 6379))
            >>> @ring.aioredis(redis_coroutine)
            >>> async def by_coroutine(...):
            >>>     ...

        Though they have slightly different behavior for `.storage.backend`:

            >>> assert by_object.storage.backend is by_object

            >>> assert by_coroutine.storage.backend is not redis_coroutine
            >>> assert isinstance(
            ...     await by_coroutine.storage.backend, aioredis.Redis)

    :see: :func:`ring.func.asyncio.CacheUserInterface` for single access
        sub-functions.
    :see: :func:`ring.func.asyncio.BulkInterfaceMixin` for bulk access
        sub-functions.

    :see: :func:`ring.redis` for non-asyncio version.
    """
    if asyncio.iscoroutine(redis):
        redis = SingletonCoroutineProxy(redis)

    return fbase.factory(
        redis, key_prefix=key_prefix, on_manufactured=factory_doctor,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        **kwargs)


def aioredis_hash(
        redis, hash_key=None, key_prefix=None, coder=None,
        user_interface=(CacheUserInterface, BulkInterfaceMixin),
        storage_class=AioredisHashStorage,
        **kwargs):
    """Redis interface for :mod:`asyncio`.

        Expected client package is aioredis_.

        This implements HASH commands in aioredis.

        aioredis expect `Redis` client or dev package is installed on your
        machine. If you are new to Memcached, check how to install it and the
        python package on your platform.

        Note that aioredis>=1.0.0 only supported.

        .. _Redis: http://redis.io/
        .. _aioredis: https://pypi.org/project/aioredis/

        :param Union[aioredis.Redis,Callable[...aioredis.Redis]] client: aioredis
            interface object. See :func:`aioredis.create_redis` or
            :func:`aioredis.create_redis_pool`. For convenience, a coroutine
            returning one of these objects also is proper. It means next 2
            examples working almost same:

                >>> redis = await aioredis.create_redis(('127.0.0.1', 6379))
                >>> @ring.aioredis_hash(redis, ...)
                >>> async def by_object(...):
                >>>     ...

                >>> redis_coroutine = aioredis.create_redis(('127.0.0.1', 6379))
                >>> @ring.aioredis_hash(redis_coroutine, ...)
                >>> async def by_coroutine(...):
                >>>     ...

        :see: :func:`ring.func.asyncio.CacheUserInterface` for single access
            sub-functions.
        :see: :func:`ring.func.asyncio.BulkInterfaceMixin` for bulk access
            sub-functions.

        :see: :func:`ring.redis` for non-asyncio version.
        """
    expire = None
    if asyncio.iscoroutine(redis):
        redis = SingletonCoroutineProxy(redis)

    return fbase.factory(
        (redis, hash_key), key_prefix=key_prefix, on_manufactured=factory_doctor,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        **kwargs)
