from __future__ import absolute_import

import six

if six.PY3:
    import inspect
    unicode = str
else:
    import inspect2 as inspect  # noqa
    unicode = unicode

try:
    from functools import lru_cache
except ImportError:  # for py2
    from functools32 import lru_cache  # noqa
