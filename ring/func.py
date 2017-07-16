"""Collection of cache decorators"""
import time
import functools
import re
import hashlib
from ring import func_base as fbase
from ring.func_base import NotFound

try:
    import asyncio
except ImportError:
    asyncio = False

__all__ = ('memcache', 'redis_py', 'redis', 'aiomcache', 'aioredis', 'arcus')


def wrapper_class(
        f, context, ckey,
        Interface, Implementation,
        miss_value,
        encode, decode):

    class Ring(fbase.WrapperBase, Interface):

        _ckey = ckey

        miss = miss_value
        impl = Implementation()

        @functools.wraps(f)
        def __call__(self, *args, **kwargs):
            args = self.reargs(args, padding=False)
            return self._get_or_update(args, kwargs)

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

        # primary primitive methods

        def _p_get(self, key):
            value = self.impl.get_value(context, key)
            return decode(value)

        def _p_set(self, key, value):
            encoded = encode(value)
            self.impl.set_value(context, key, encoded)

        def _p_delete(self, key):
            self.impl.del_value(context, key)

        def _p_touch(self, key):
            self.impl.touch_value(context, key)

        def _p_execute(self, args, kwargs):
            result = f(*args, **kwargs)
            return result

    return Ring


class CacheInterface(fbase.BaseInterface):

    def _get(self, args, kwargs):
        key = self._key(args, kwargs)
        try:
            result = self._p_get(key)
        except NotFound:
            result = self.miss
        return result

    def _update(self, args, kwargs):
        key = self._key(args, kwargs)
        result = self._p_execute(args, kwargs)
        self._p_set(key, result)
        return result

    def _get_or_update(self, args, kwargs):
        key = self._key(args, kwargs)
        try:
            result = self._p_get(key)
        except NotFound:
            result = self._p_execute(args, kwargs)
            self._p_set(key, result)
        return result

    def _delete(self, args, kwargs):
        key = self._key(args, kwargs)
        self._p_delete(key)

    def _touch(self, args, kwargs):
        key = self._key(args, kwargs)
        self._p_touch(key)


def dict(
        obj, key_prefix='', expire=None, coder=None, ignorable_keys=None,
        interface=CacheInterface,
        now=time.time):

    class Impl(fbase.Implementation):

        def now(self):
            if callable(now):
                _now = now()
            else:
                _now = now
            return _now

        def get_value(self, obj, key):
            _now = self.now()
            try:
                expired_time, value = obj[key]
            except KeyError:
                raise fbase.NotFound
            if expired_time is not None and expired_time < _now:
                raise fbase.NotFound
            return value

        def set_value(self, obj, key, value):
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
        interface=interface, implementation=Impl,
        miss_value=None, coder=coder,
        ignorable_keys=ignorable_keys)


def memcache(
        client, key_prefix=None, time=0, coder=None, ignorable_keys=None,
        interface=CacheInterface):
    from ring._memcache import key_refactor
    miss_value = None

    class Impl(fbase.Implementation):
        def get_value(self, client, key):
            value = client.get(key)
            if value is None:
                raise fbase.NotFound
            return value

        def set_value(self, client, key, value):
            client.set(key, value, time)

        def del_value(self, client, key):
            client.delete(key)

        def touch_value(self, client, key):
            client.touch(key, time)

    return fbase.factory(
        client, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=interface, implementation=Impl,
        miss_value=miss_value, coder=coder,
        ignorable_keys=ignorable_keys,
        key_refactor=key_refactor)


def redis_py(
        client, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        interface=CacheInterface):

    class Impl(fbase.Implementation):
        def get_value(self, client, key):
            value = client.get(key)
            if value is None:
                raise fbase.NotFound
            return value

        def set_value(self, client, key, value):
            client.set(key, value, expire)

        def del_value(self, client, key):
            client.delete(key)

        def touch_value(self, client, key):
            if expire is None:
                raise TypeError("'touch' is requested for persistant cache")
            client.expire(key, expire)

    return fbase.factory(
        client, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=interface, implementation=Impl,
        miss_value=None, coder=coder,
        ignorable_keys=ignorable_keys)


def arcus(
        client, key_prefix=None, time=0, coder=None, ignorable_keys=None,
        interface=CacheInterface):

    class Impl(fbase.Implementation):
        def get_value(self, client, key):
            value = client.get(key).get_result()
            if value is None:
                raise fbase.NotFound
            return value

        def set_value(self, client, key, value):
            client.set(key, value, time)

        def del_value(self, client, key):
            client.delete(key)

        def touch_value(self, client, key):
            client.touch(key, time)

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
        client, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=interface, implementation=Impl,
        miss_value=None, coder=coder,
        ignorable_keys=ignorable_keys,
        key_refactor=key_refactor)


# de facto standard of redis
redis = redis_py


if asyncio:
    from ring.func_asyncio import aiomcache, aioredis
