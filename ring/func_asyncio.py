"""Collection of cache decorators"""
import asyncio
import inspect
import functools
import time
from ring import func_base as fbase

inspect_iscoroutinefunction = getattr(inspect, 'iscoroutinefunction', lambda f: False)


def _is_coroutine(f):
    return hasattr(f, '_is_coroutine') or inspect_iscoroutinefunction(f)


def wrapper_class(
        f, context, ckey,
        Interface, Implementation,
        miss_value,
        encode, decode):

    if not _is_coroutine(f):
        raise TypeError(
            "The funciton for cache '{}' must be an async function.".format(
                f.__name__))

    class Ring(fbase.WrapperBase, Interface):

        _ckey = ckey

        NotFound = fbase.NotFound
        miss = miss_value
        impl = Implementation()

        def __getattr__(self, name):
            try:
                return self.__getattribute__(name)
            except:
                pass

            interface_name = '_' + name
            if hasattr(Interface, interface_name):
                attr = getattr(self, interface_name)
                if callable(attr):
                    @functools.wraps(f)
                    def impl_f(*args, **kwargs):
                        args = self.reargs(args, padding=True)
                        return attr(args, kwargs)
                    setattr(self, name, impl_f)

            return self.__getattribute__(name)

        @functools.wraps(f)
        def __call__(self, *args, **kwargs):
            args = self.reargs(args, padding=False)
            return self._get_or_update(args, kwargs)

        def _key(self, args, kwargs):
            key = self._ckey.build_key(args, kwargs)
            print(key, args, kwargs)
            return key

        @asyncio.coroutine
        def _p_get(self, key):
            value = yield from self.impl.get_value(context, key)
            return decode(value)

        @asyncio.coroutine
        def _p_set(self, key, value):
            encoded = encode(value)
            yield from self.impl.set_value(context, key, encoded)

        @asyncio.coroutine
        def _p_delete(self, key):
            yield from self.impl.del_value(context, key)

        @asyncio.coroutine
        def _p_touch(self, key):
            yield from self.impl.touch_value(context, key)

        @asyncio.coroutine
        def _p_execute(self, args, kwargs):
            result = yield from f(*args, **kwargs)
            return result

    return Ring


class CacheInterface(fbase.BaseInterface):

    @asyncio.coroutine
    def _get(self, args, kwargs):
        key = self._key(args, kwargs)
        try:
            result = yield from self._p_get(key)
        except self.NotFound:
            result = self.miss
        return result

    @asyncio.coroutine
    def _update(self, args, kwargs):
        key = self._key(args, kwargs)
        result = yield from self._p_execute(args, kwargs)
        yield from self._p_set(key, result)
        return result

    @asyncio.coroutine
    def _get_or_update(self, args, kwargs):
        key = self._key(args, kwargs)
        try:
            result = yield from self._p_get(key)
        except self.NotFound:
            result = yield from self._p_execute(args, kwargs)
            yield from self._p_set(key, result)
        return result

    @asyncio.coroutine
    def _delete(self, args, kwargs):
        key = self._key(args, kwargs)
        yield from self._p_delete(key)

    @asyncio.coroutine
    def _touch(self, args, kwargs):
        key = self._key(args, kwargs)
        yield from self._p_touch(key)


def async_dict(
        obj, key_prefix='', expire=None, coder=None, ignorable_keys=None,
        now=time.time):

    class Impl(fbase.Implementation):

        def now(self):
            if callable(now):
                _now = now()
            else:
                _now = now
            return _now

        @asyncio.coroutine
        def get_value(self, obj, key):
            _now = self.now()

            try:
                expired_time, value = obj[key]
            except KeyError:
                raise fbase.NotFound

            if expired_time is not None and expired_time < _now:
                raise fbase.NotFound

            return value

        @asyncio.coroutine
        def set_value(self, obj, key, value):
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
        def touch_value(self, obj, key):
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

    return fbase.factory(
        obj, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=CacheInterface, implementation=Impl,
        miss_value=None, coder=coder,
        ignorable_keys=ignorable_keys)


def aiomcache(
        client, key_prefix, time=0, coder=None, ignorable_keys=None,
        key_encoding='utf-8'):
    from ring._memcache import key_refactor

    class Impl(fbase.Implementation):
        @asyncio.coroutine
        def get_value(self, client, key):
            value = yield from client.get(key)
            if value is None:
                raise fbase.NotFound
            return value

        def set_value(self, client, key, value):
            return client.set(key, value, time)

        def del_value(self, client, key):
            return client.delete(key)

        def touch_value(self, client, key):
            return client.touch(key, time)

    return fbase.factory(
        client, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=CacheInterface, implementation=Impl,
        miss_value=None, coder=coder,
        ignorable_keys=ignorable_keys,
        key_encoding=key_encoding,
        key_refactor=key_refactor)


def aioredis(pool, key_prefix, expire, coder=None, ignorable_keys=None):

    class Impl(fbase.Implementation):
        @asyncio.coroutine
        def get_value(self, pool, key):
            client = yield from pool.acquire()
            try:
                value = yield from client.get(key)
            finally:
                pool.release(client)
            if value is None:
                raise fbase.NotFound
            return value

        @asyncio.coroutine
        def set_value(self, pool, key, value):
            client = yield from pool.acquire()
            try:
                yield from client.set(key, value, expire=expire)
            finally:
                pool.release(client)

        @asyncio.coroutine
        def del_value(self, pool, key):
            client = yield from pool.acquire()
            try:
                yield from client.delete(key)
            finally:
                pool.release(client)

        @asyncio.coroutine
        def touch_value(self, pool, key):
            client = yield from pool.acquire()
            try:
                client.expire(key, expire)
            finally:
                pool.release(client)

    return fbase.factory(
        pool, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=CacheInterface, implementation=Impl,
        miss_value=None, coder=coder,
        ignorable_keys=ignorable_keys)
