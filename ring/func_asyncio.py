"""Collection of cache decorators"""
import asyncio
import inspect
import functools
import time
from ring import _func_util as futil

inspect_iscoroutinefunction = getattr(inspect, 'iscoroutinefunction', None)


def _is_coroutine(f):
    return hasattr(f, '_is_coroutine') or \
        (inspect_iscoroutinefunction and inspect_iscoroutinefunction(f))


def _factory(
        context, key_prefix,
        get_value, set_value, del_value, touch_value, miss_value, coder,
        ignorable_keys=None, key_encoding=None):

    encode, decode = futil.unpack_coder(coder)

    def _decorator(f):
        if not _is_coroutine(f):
            raise TypeError(
                "The funciton for cache '{}' must be an async function.".format(
                    f.__name__))

        _ignorable_keys = futil.suggest_ignorable_keys(f, ignorable_keys)
        _key_prefix = futil.suggest_key_prefix(f, key_prefix)
        ckey = futil.create_ckey(
            f, _key_prefix, _ignorable_keys, key_encoding)

        class _Wrapper(futil.WrapperBase):

            _key = ckey

            @functools.wraps(f)
            def __call__(self, *args, **kwargs):
                args = self.reargs(args, padding=False)
                return self._get_or_update(*args, **kwargs)

            def key(self, *args, **kwargs):
                return self._key.build_key(args, kwargs)

            @asyncio.coroutine
            def _get_or_update(self, *args, **kwargs):
                key = self.key(*args, **kwargs)
                value = yield from get_value(context, key)
                if value == miss_value:
                    result = yield from f(*args, **kwargs)
                    value = encode(result)
                    yield from set_value(context, key, value)
                else:
                    result = decode(value)
                return value

            def get_or_update(self, *args, **kwargs):
                args = self.reargs(args, padding=True)
                return self._get_or_update(*args, **kwargs)

            @asyncio.coroutine
            def get(self, *args, **kwargs):
                args = self.reargs(args, padding=True)
                key = self.key(*args, **kwargs)
                value = yield from get_value(context, key)
                if value == miss_value:
                    return miss_value
                else:
                    return decode(value)

            @asyncio.coroutine
            def update(self, *args, **kwargs):
                args = self.reargs(args, padding=True)
                key = self.key(*args, **kwargs)
                result = yield from f(*args, **kwargs)
                value = encode(result)
                yield from set_value(context, key, value)
                return result

            def delete(self, *args, **kwargs):
                args = self.reargs(args, padding=True)
                key = self.key(*args, **kwargs)
                return del_value(context, key)

            def touch(self, *args, **kwargs):
                args = self.reargs(args, padding=True)
                key = self.key(*args, **kwargs)
                return touch_value(context, key)

        if futil.is_method(f):
            @property
            def _w(self):
                return _Wrapper((self,))
        elif futil.is_classmethod(f):
            _w = _Wrapper((), anon_padding=True)
        else:
            _w = _Wrapper(())

        return _w

    return _decorator


def async_dict(obj, key_prefix='', expire=None, coder=None, ignorable_keys=None, now=time.time):
    miss_value = None

    @asyncio.coroutine
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

    @asyncio.coroutine
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

    @asyncio.coroutine
    def del_value(obj, key):
        try:
            del obj[key]
        except KeyError:
            pass

    @asyncio.coroutine
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
        ignorable_keys=ignorable_keys)


def aiomcache(client, key_prefix, time=0, coder=None, ignorable_keys=None, key_encoding='utf-8'):
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
        ignorable_keys=ignorable_keys,
        key_encoding=key_encoding)


def aioredis(pool, key_prefix, expire, coder=None, ignorable_keys=None):
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
        ignorable_keys=ignorable_keys)
