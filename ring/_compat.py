from __future__ import absolute_import

import six

import functools

if not hasattr(functools, "lru_cache"):
    import functools32

    functools.lru_cache = functools32.lru_cache

if six.PY3:
    import inspect

    unicode = str
else:
    import inspect2 as inspect  # noqa

    unicode = unicode


def qualname(x):
    if six.PY34:
        return x.__qualname__

    # not perfect - but it is ok for cache key
    if hasattr(x, "im_class"):
        return ".".join((x.im_class.__name__, x.__name__))
    else:
        return x.__name__
