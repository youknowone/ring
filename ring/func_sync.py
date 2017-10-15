"""Collection of cache decorators"""
import time
import functools
import re
import hashlib
from ring import func_base as fbase
from ring.wire import Wire
from ring.func_base import NotFound

__all__ = ('memcache', 'redis_py', 'redis', 'arcus')


def wrapper_class(
        f, storage, ckey,
        Interface, Storage,
        miss_value, expire_default,
        encode, decode):

    class Ring(Wire, Interface):

        _ckey = ckey
        _expire_default = expire_default

        _storage = storage
        _miss_value = miss_value
        _storage_impl = Storage()
        _encode = staticmethod(encode)
        _decode = staticmethod(decode)

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

        def _p_execute(self, args, kwargs):
            result = f(*args, **kwargs)
            return result

        def _p_get(self, key):
            value = self._storage_impl.get_value(self._storage, key)
            return self._decode(value)

        def _p_set(self, key, value, expire=expire_default):
            encoded = self._encode(value)
            self._storage_impl.set_value(self._storage, key, encoded, expire)

        def _p_delete(self, key):
            self._storage_impl.del_value(self._storage, key)

        def _p_touch(self, key, expire=expire_default):
            self._storage_impl.touch_value(self._storage, key, expire)

    return Ring


class CacheInterface(fbase.BaseInterface):

    def _get(self, args, kwargs):
        key = self._key(args, kwargs)
        try:
            result = self._p_get(key)
        except NotFound:
            result = self._miss_value
        return result

    def _update(self, args, kwargs):
        key = self._key(args, kwargs)
        result = self._p_execute(args, kwargs)
        self._p_set(key, result, self._expire_default)
        return result

    def _get_or_update(self, args, kwargs):
        key = self._key(args, kwargs)
        try:
            result = self._p_get(key)
        except NotFound:
            result = self._p_execute(args, kwargs)
            self._p_set(key, result, self._expire_default)
        return result

    def _delete(self, args, kwargs):
        key = self._key(args, kwargs)
        self._p_delete(key)

    def _touch(self, args, kwargs):
        key = self._key(args, kwargs)
        self._p_touch(key)


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
        obj, key_prefix='', expire=None, coder=None, ignorable_keys=None,
        interface=CacheInterface, storage_implementation=DictImpl):

    return fbase.factory(
        obj, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=interface, storage_implementation=storage_implementation,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)


def memcache(
        client, key_prefix=None, time=0, coder=None, ignorable_keys=None,
        interface=CacheInterface, storage_implementation=MemcacheImpl):
    from ring._memcache import key_refactor
    miss_value = None

    return fbase.factory(
        client, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=interface, storage_implementation=storage_implementation,
        miss_value=miss_value, expire_default=time, coder=coder,
        ignorable_keys=ignorable_keys,
        key_refactor=key_refactor)


def redis_py(
        client, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        interface=CacheInterface, storage_implementation=RedisImplementation):

    return fbase.factory(
        client, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=interface, storage_implementation=storage_implementation,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)


# de facto standard of redis
redis = redis_py


def arcus(
        client, key_prefix=None, time=0, coder=None, ignorable_keys=None,
        interface=CacheInterface):

    class Impl(fbase.Storage):
        def get_value(self, client, key):
            value = client.get(key).get_result()
            if value is None:
                raise fbase.NotFound
            return value

        def set_value(self, client, key, value):
            client.set(key, value, time)

        def del_value(self, client, key):
            client.delete(key)

        def touch_value(self, client, key, expire=time):
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
        client, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=interface, storage_implementation=Impl,
        miss_value=None, expire_default=time, coder=coder,
        ignorable_keys=ignorable_keys,
        key_refactor=key_refactor)
