"""Collection of cache decorators"""
import asyncio
import inspect
from ring._func_util import _unpack_coder, _create_ckey

inspect_iscoroutinefunction = getattr(inspect, 'iscoroutinefunction', None)


def _is_coroutine(f):
    return hasattr(f, '_is_coroutine') or \
        (inspect_iscoroutinefunction and inspect_iscoroutinefunction(f))


def _factory(
        context, key_prefix,
        get_value, set_value, del_value, touch_value, miss_value, coder,
        args_prefix_size=None, ignorable_keys=None, key_encoding=None):

    encode, decode = _unpack_coder(coder)

    def _decorator(f):
        if not _is_coroutine(f):
            raise TypeError(
                "The funciton for cache '{}' must be an async function.".format(
                    f.__name__))

        ckey = _create_ckey(
            f, key_prefix, args_prefix_size, ignorable_keys, key_encoding)

        @asyncio.coroutine
        def _get_or_update(*args, **kwargs):
            key = ckey.build_key(args, kwargs)
            value = yield from get_value(context, key)
            if value == miss_value:
                result = yield from f(*args, **kwargs)
                value = encode(result)
                yield from set_value(context, key, value)
            else:
                result = decode(value)
            return value

        @asyncio.coroutine
        def _get(*args, **kwargs):
            key = ckey.build_key(args, kwargs)
            value = yield from get_value(context, key)
            if value == miss_value:
                return miss_value
            else:
                return decode(value)

        @asyncio.coroutine
        def _update(*args, **kwargs):
            key = ckey.build_key(args, kwargs)
            result = yield from f(*args, **kwargs)
            value = encode(result)
            yield from set_value(context, key, value)
            return result

        def _delete(*args, **kwargs):
            key = ckey.build_key(args, kwargs)
            return del_value(context, key)

        def _touch(*args, **kwargs):
            key = ckey.build_key(args, kwargs)
            return touch_value(context, key)

        _f = _get_or_update
        _f.get = _get
        _f.update = _update
        _f.get_or_update = _get_or_update
        _f.delete = _delete
        if touch_value:
            _f.touch = _touch

        return _f

    return _decorator


def aiomcache(client, key_prefix, time=0, coder=None, args_prefix_size=None, ignorable_keys=None, key_encoding='utf-8'):
    miss_value = None

    def get_value(client, key):
        return client.get(key)

    def set_value(client, key, value):
        return client.set(key, value, time)

    def del_value(client, key):
        return client.delete(key)

    def touch_value(client, key):
        return client.touch(key, time)

    return _factory(
        client, key_prefix=key_prefix,
        get_value=get_value, set_value=set_value, del_value=del_value,
        touch_value=touch_value,
        miss_value=miss_value, coder=coder,
        args_prefix_size=args_prefix_size, ignorable_keys=ignorable_keys,
        key_encoding=key_encoding)


def aioredis(pool, key_prefix, expire, coder=None, args_prefix_size=None, ignorable_keys=None):
    miss_value = None

    @asyncio.coroutine
    def get_value(pool, key):
        client = yield from pool.acquire()
        try:
            value = yield from client.get(key)
        finally:
            pool.release(client)
        return value

    @asyncio.coroutine
    def set_value(pool, key, value):
        client = yield from pool.acquire()
        try:
            yield from client.set(key, value, expire=expire)
        finally:
            pool.release(client)

    @asyncio.coroutine
    def del_value(pool, key):
        client = yield from pool.acquire()
        try:
            yield from client.delete(key)
        finally:
            pool.release(client)

    @asyncio.coroutine
    def touch_value(pool, key):
        client = yield from pool.acquire()
        try:
            client.expire(key, expire)
        finally:
            pool.release(client)

    return _factory(
        pool, key_prefix=key_prefix,
        get_value=get_value, set_value=set_value, del_value=del_value,
        touch_value=touch_value,
        miss_value=miss_value, coder=coder,
        args_prefix_size=args_prefix_size, ignorable_keys=ignorable_keys)
