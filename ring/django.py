""":mod:`ring.django` --- Django support
========================================
"""
from __future__ import absolute_import

import warnings
from typing import Any, Optional, Tuple
from django.core import cache as django_cache
from django.http.request import HttpRequest
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.cache import get_cache_key
from django.middleware.cache import CacheMiddleware
from .func import base as fbase
from .func.sync import CacheUserInterface


__all__ = ('cache', 'cache_page')


def promote_backend(backend):
    """Get string name to django cache backend."""
    if isinstance(backend, (str, bytes)):
        backend = django_cache.caches[backend]
    return backend


class LowLevelCacheStorage(fbase.CommonMixinStorage, fbase.StorageMixin):
    """Storage implementation for :data:`django.core.cache.caches`."""

    def get_value(self, key):
        value = self.backend.get(key)
        if value is None:
            raise fbase.NotFound
        return value

    def set_value(self, key, value, expire):
        self.backend.set(key, value, timeout=expire)

    def delete_value(self, key):
        self.backend.delete(key)


def transform_cache_page_args(wire, rules, args, kwargs):
    raw_request = args[0]
    if isinstance(raw_request, HttpRequest):
        request = raw_request
    elif type(raw_request) == tuple:
        template_request, path_hint = raw_request
        if not isinstance(template_request, HttpRequest):
            raise TypeError
        request = HttpRequest()
        request.__dict__.update(template_request.__dict__)
        request._fake_request = True
        request.method = 'GET'
        if path_hint is not None:
            try:
                path = reverse(path_hint)
            except NoReverseMatch:
                path = path_hint
            request.path = path
    else:
        request = raw_request  # type error?

    return (request, ) + args[1:], kwargs


class CachePageUserInterface(fbase.BaseUserInterface):
    """Django per-view cache interface.

    :note: This interface doesn't require any storage backend.

    The interface imitates the behavior of
    :func:`django.views.decorators.cache.cache_page`. The code is mostly parts
    of fragmented :func:`django.utils.decorators.make_middleware_decorator`
    except for `key`, `delete` and `has`.
    """

    @property
    def middleware(self):
        return self.ring.storage.backend

    @fbase.interface_attrs(
        transform_args=transform_cache_page_args,
        return_annotation=Tuple[str, str])
    def key(self, wire, request, *args, **kwargs):
        middleware = self.middleware
        key_get = get_cache_key(
            request, middleware.key_prefix, 'GET', cache=middleware.cache)
        key_head = get_cache_key(
            request, middleware.key_prefix, 'HEAD', cache=middleware.cache)
        return key_get, key_head

    @fbase.interface_attrs(
        transform_args=transform_cache_page_args)
    def execute(self, wire, request, *args, **kwargs):
        middleware = self.middleware
        view_func = wire.__func__
        try:
            response = view_func(request, *args, **kwargs)
        except Exception as e:
            if hasattr(middleware, 'process_exception'):
                result = middleware.process_exception(request, e)
                if result is not None:
                    return result
            raise
        if hasattr(response, 'render') and callable(response.render):
            if hasattr(middleware, 'process_template_response'):
                response = middleware.process_template_response(
                    request, response)
        return response

    @fbase.interface_attrs(
        transform_args=transform_cache_page_args,
        return_annotation=lambda a: Optional[a.get('return', Any)])
    def get(self, wire, request, *args, **kwargs):
        middleware = self.middleware
        result = middleware.process_request(request)
        if result is not None:
            return result
        # no 'precess_view' in CacheMiddleware
        # if hasattr(middleware, 'process_view'):
        #    result = middleware.process_view(request, view_func, args, kwargs)
        #    if result is not None:
        #        return result
        return self.ring.miss_value

    @fbase.interface_attrs(
        transform_args=transform_cache_page_args, return_annotation=None)
    def set(self, wire, response, request, *args, **kwargs):
        if not hasattr(request, '_cache_update_cache'):
            request._cache_update_cache = request.method in ('GET', 'HEAD')
        middleware = self.middleware
        if hasattr(response, 'render') and callable(response.render):
            if hasattr(middleware, 'process_response'):
                def callback(response):
                    return middleware.process_response(request, response)

                response.add_post_render_callback(callback)
        else:
            if hasattr(middleware, 'process_response'):
                return middleware.process_response(request, response)

    @fbase.interface_attrs(
        transform_args=transform_cache_page_args, return_annotation=None)
    def update(self, wire, request, *args, **kwargs):
        response = self.execute(wire, request, *args, **kwargs)
        self.set(wire, response, request, *args, **kwargs)
        return response

    @fbase.interface_attrs(
        transform_args=transform_cache_page_args)
    def get_or_update(self, wire, request, *args, **kwargs):
        response = self.get(wire, request, *args, **kwargs)
        if response is not None:
            return response
        response = self.execute(wire, request, *args, **kwargs)
        self.set(wire, response, request, *args, **kwargs)
        return response

    @fbase.interface_attrs(
        transform_args=transform_cache_page_args, return_annotation=None)
    def delete(self, wire, request, *args, **kwargs):
        if not getattr(request, '_fake_request', None):
            warnings.warn(
                "A request is given as first argument. If this is intended "
                "try '(request, None)'. Otherwise, Use '(request, path)' "
                "instead of 'request' to convert the actual request to have "
                "the target path.")
        key_get, key_head = self.key(wire, request, *args, **kwargs)
        if key_get:
            self.middleware.cache.delete(key_get)
        if key_head:
            self.middleware.cache.delete(key_head)

    @fbase.interface_attrs(
        transform_args=transform_cache_page_args, return_annotation=bool)
    def has(self, *args, **kwargs):
        raise NotImplementedError
        # The below implementation is not reliable for the return value `True`.
        # `False` always means the cache doesn't exist; While `True` doesn't
        # guarantee the cache is valid.
        # return self.key(*args, **kwargs) != (None, None)

    @fbase.interface_attrs(
        transform_args=transform_cache_page_args, return_annotation=None)
    def touch(self, wire, request, *args, **kwargs):  #
        raise NotImplementedError


def cache(
        backend=django_cache.cache, key_prefix=None, expire=None, coder=None,
        ignorable_keys=None,
        user_interface=CacheUserInterface, storage_class=LowLevelCacheStorage):
    """A typical ring-style cache based on Django's low-level cache API.

    :param Union[str,object] backend: Django's cache config key for
           :data:`django.core.cache.caches` or Django cache object.

    :see: `Django's cache framework: Setting up the cache`_ to configure django
        cache.
    :see: `Django's cache framework: The low-level cache API`_ for the backend.

    .. _`Django's cache framework: Setting up the cache`: https://docs.djangoproject.com/en/2.0/topics/cache/#setting-up-the-cache
    .. _`Django's cache framework: The low-level cache API`: https://docs.djangoproject.com/en/2.0/topics/cache/#the-low-level-cache-api
    """  # noqa
    backend = promote_backend(backend)
    return fbase.factory(
        backend, key_prefix=key_prefix, on_manufactured=None,
        user_interface=user_interface, storage_class=storage_class,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)


def cache_page(
        timeout, cache=None, key_prefix=None,  # original parameters
        user_interface=CachePageUserInterface,
        storage_class=fbase.BaseStorage):
    """The drop-in-replacement of Django's per-view cache.

    Use this decorator instead of
    :func:`django.views.decorators.cache.cache_page`.
    The decorated view function itself is compatible. Ring decorated function
    additionally have ring-styled sub-functions. In the common cases, `delete`
    and `update` are helpful.

    :param float timeout: Same as `timeout` of Django's `cache_page`.
    :param Optional[str] cache: Same as `cache` of Django's `cache_page`.
    :param str key_prefix: Same as `key_prefix` of Django's `cache_page`.

    Here is an example of `delete` sub-function.

    .. code-block:: python

        @ring.django.cache_page(timeout=60)
        def article_list(request):
            articles = ...
            return HttpResponse(
                template.render({'articles': articles}, request))

        def article_post(request):
            article = ...  # create a new article
            article_list.delete((request, 'article_list'))  # DELETE!
            return ...

    Compare to how django originally invalidate it.

    .. code-block:: python

        def article_post_django(request):
            articles = ...

            from django.core.cache import cache
            from django.utils.cache import get_cache_key
            fake_request = HttpRequest()  # a fake request
            fake_request.__dict__.update(request.__dict__)  # not mandatory by env
            fake_request.method = 'GET'
            fake_request.path = reverse('article_list')
            key = get_cache_key(request)
            cache.delete(key)

            return ...

    Note that the first parameter of every sub-function originally is an
    :class:`django.request.HttpRequest` object but a tuple here.
    The second item of the tuple provides a hint for the request path of
    `article_list`. Because Django expects the cache key varies by request
    path, it is required to find the corresponding cache key.

    :see: `Django's cache framework: The per-view cache <https://docs.djangoproject.com/en/2.0/topics/cache/#the-per-view-cache>`_

    :see: :func:`django.views.decorators.cache.cache_page`.
    """  # noqa
    middleware_class = CacheMiddleware
    middleware = middleware_class(
        cache_timeout=timeout, cache_alias=cache, key_prefix=key_prefix)

    return fbase.factory(
        middleware, key_prefix='', on_manufactured=None,
        user_interface=user_interface, storage_class=storage_class,
        # meaningless parameters below
        miss_value=None, expire_default=None, coder=None)
