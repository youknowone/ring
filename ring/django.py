""":mod:`ring.django` --- Django support
========================================
"""
from __future__ import absolute_import

import functools
from django.core import cache
from . import func_base as fbase
from .func_sync import CacheUserInterface


__all__ = ('django', 'django_default')


def promote_backend(backend):
    """Get string name to django cache backend."""
    if isinstance(backend, (str, bytes)):
        backend = cache.caches[backend]
    return backend


class DjangoStorage(fbase.CommonMixinStorage, fbase.StorageMixin):
    def get_value(self, key):
        value = self.backend.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, key, value, expire):
        self.backend.set(key, value, timeout=expire)

    def delete_value(self, key):
        self.backend.delete(key)


def django(
        backend, key_prefix=None, expire=None, coder=None, ignorable_keys=None,
        user_interface=CacheUserInterface, storage_class=DjangoStorage):
    """Django cache interface based on low-level cache API.

    :param Union[str,object] backend: Django's cache config key for
           :data:`django.core.cache.caches` or Django cache object.

    :see: :data:`ring.django.django_default` shortcut for common `default` configuration.
    :see: `Django's cache framework: Setting up the cache`_ to configure django cache.
    :see: `Django's cache framework: The low-level cache API`_ for the backend.

    .. _`Django's cache framework: Setting up the cache`: https://docs.djangoproject.com/en/2.0/topics/cache/#setting-up-the-cache
    .. _`Django's cache framework: The low-level cache API`: https://docs.djangoproject.com/en/2.0/topics/cache/#the-low-level-cache-api
    """
    backend = promote_backend(backend)
    return fbase.factory(
        backend, key_prefix=key_prefix, on_manufactured=None,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)


#: Shortcut for common `default` configuration.
#: :see: :data:`ring.django.django` for generic form.
django_default = functools.partial(django, cache.cache)
