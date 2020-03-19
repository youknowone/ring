from __future__ import absolute_import

from wirerope.callable import Callable
from ._util import cached_property
from ._compat import qualname

__all__ = ('Callable', )


def _code(self):
    """REAL __code__ for the given callable."""
    code_owner = self.wrapped_callable
    if self.is_wrapped_coroutine:
        code_owner = code_owner.__wrapped__
    return code_owner.__code__


def _annotations(self):
    return getattr(self.wrapped_callable, '__annotations__', None) or {}


def _identifier(self):
    return '.'.join((
        self.wrapped_callable.__module__, qualname(self.wrapped_callable)))


Callable.code = cached_property(_code)
Callable.annotations = property(_annotations)
Callable.identifier = cached_property(_identifier)
