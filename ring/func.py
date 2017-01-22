"""Collection of cache decorators"""
import functools
import time
from ring._func_util import _unpack_coder, _create_ckey

try:
    import asyncio
except ImportError:
    asyncio = False

__all__ = ('memcache', 'redis_py', 'redis', 'aiomcache', 'aioredis')


def _factory(
        context, key_prefix,
        get_value, set_value, del_value, touch_value, miss_value, coder,
        args_prefix_size=None, ignorable_keys=None, key_encoding=None):

    encode, decode = _unpack_coder(coder)

    def _decorator(f):

        ckey = _create_ckey(
            f, key_prefix, args_prefix_size, ignorable_keys, key_encoding)

        @functools.wraps(f)
        def _get_or_update(*args, **kwargs):
            key = ckey.build_key(args, kwargs)
            value = get_value(context, key)
            if value == miss_value:
                result = f(*args, **kwargs)
                value = encode(result)
                set_value(context, key, value)
            else:
                result = decode(value)
            return value

        def _get(*args, **kwargs):
            key = ckey.build_key(args, kwargs)
            value = get_value(context, key)
            if value == miss_value:
                return miss_value
            else:
                return decode(value)

        def _update(*args, **kwargs):
            key = ckey.build_key(args, kwargs)
            result = f(*args, **kwargs)
            value = encode(result)
            set_value(context, key, value)
            return result

        def _delete(*args, **kwargs):
            key = ckey.build_key(args, kwargs)
            del_value(context, key)

        def _touch(*args, **kwargs):
            key = ckey.build_key(args, kwargs)
            touch_value(context, key)

        _f = _get_or_update
        _f.get = _get
        _f.update = _update
        _f.get_or_update = _get_or_update
        _f.delete = _delete
        if touch_value:
            _f.touch = _touch

        return functools.wraps(f)(_f)

    return _decorator


def dict(obj, key_prefix='', expire=None, coder=None, args_prefix_size=None, ignorable_keys=None, now=time.time):
    miss_value = None

    def get_value(obj, key):
        if now is None:
            _now = time.time()
        else:
            _now = now
        try:
            expired_time, value = obj[key]
        except KeyError:
            return miss_value
        if expired_time is not None and expired_time < _now:
            return miss_value
        return value

    def set_value(obj, key, value):
        if now is None:
            _now = time.time()
        else:
            _now = now
        if expire is None:
            expired_time = None
        else:
            expired_time = _now + expire
        obj[key] = expired_time, value

    def del_value(obj, key):
        try:
            del obj[key]
        except KeyError:
            pass

    def touch_value(obj, key):
        if now is None:
            _now = time.time()
        else:
            _now = now
        try:
            expired_time, value = obj[key]
        except KeyError:
            return
        if expire is None:
            expired_time = None
        else:
            expired_time = _now + expire
        obj[key] = expired_time, value

    return _factory(
        obj, key_prefix=key_prefix,
        get_value=get_value, set_value=set_value, del_value=del_value,
        touch_value=touch_value,
        miss_value=miss_value, coder=coder,
        args_prefix_size=args_prefix_size, ignorable_keys=ignorable_keys)


def memcache(client, key_prefix, time=0, coder=None, args_prefix_size=None, ignorable_keys=None):
    miss_value = None

    def get_value(client, key):
        value = client.get(key)
        return value

    def set_value(client, key, value):
        client.set(key, value, time)

    def del_value(client, key):
        client.delete(key)

    def touch_value(client, key):
        client.touch(key, time)

    return _factory(
        client, key_prefix=key_prefix,
        get_value=get_value, set_value=set_value, del_value=del_value,
        touch_value=touch_value,
        miss_value=miss_value, coder=coder,
        args_prefix_size=args_prefix_size, ignorable_keys=ignorable_keys)


def redis_py(client, key_prefix, expire, coder=None, args_prefix_size=None, ignorable_keys=None):
    miss_value = None

    def get_value(client, key):
        value = client.get(key)
        return value

    def set_value(client, key, value):
        client.set(key, value, expire)

    def del_value(client, key):
        client.delete(key)

    def touch_value(client, key):
        client.expire(key, expire)

    return _factory(
        client, key_prefix=key_prefix,
        get_value=get_value, set_value=set_value, del_value=del_value,
        touch_value=touch_value,
        miss_value=miss_value, coder=coder,
        args_prefix_size=args_prefix_size, ignorable_keys=ignorable_keys)


redis = redis_py  # de facto standard of redis


if asyncio:
    from ring.func_asyncio import aiomcache, aioredis
