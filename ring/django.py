from __future__ import absolute_import
import functools
from django.core.cache import caches
from ring import func_base as fbase
from ring.func_sync import ring_factory, CacheInterface


__all__ = ('django', 'django_default')


def promote_backend(backend):
    if isinstance(backend, (str, bytes)):
        backend = caches[backend]
    return backend


class DjangoImpl(fbase.StorageImplementation):
    def get_value(self, backend, key):
        value = backend.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, backend, key, value, expire):
        backend.set(key, value, timeout=expire)

    def del_value(self, backend, key):
        backend.delete(key)


def django(
        backend, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        interface=CacheInterface, storage_implementation=DjangoImpl):
    backend = promote_backend(backend)
    return fbase.factory(
        backend, key_prefix=key_prefix, ring_factory=ring_factory,
        interface=interface, storage_implementation=storage_implementation,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)


django_default = functools.partial(django, 'default')
