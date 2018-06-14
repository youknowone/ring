from __future__ import absolute_import

import collections
from wirerope.callable import Callable
from ._util import cached_property
from ._compat import inspect, qualname

__all__ = ('Callable', )


def _code(self):
    """REAL __code__ for the given callable."""
    code_owner = self.wrapped_callable
    if self.is_wrapped_coroutine:
        code_owner = code_owner.__wrapped__
    return code_owner.__code__


def _annotations(self):
    return getattr(self.wrapped_callable, '__annotations__', None) or {}


def _kwargify(self, args, kwargs, bound_args=()):
    """Create a merged kwargs-like object with given args and kwargs."""
    merged = collections.OrderedDict()

    parameters = self.parameters
    parameters_len = len(parameters)

    consumed_i = 0
    consumed_names = set()
    i = 0

    # no .POSITIONAL_ONLY support

    if bound_args:
        while i in bound_args:
            i += 1

    while i < parameters_len and \
            parameters[i].kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
        p = parameters[i]
        i += 1

        name = p.name
        try:
            value = args[consumed_i]
        except IndexError:
            pass
        else:
            if name in kwargs:
                raise TypeError(
                    "{}() got multiple values for argument '{}'".format(
                        self.code.co_name, name))
            consumed_i += 1
            merged[name] = value
            continue

        if name in kwargs:
            merged[name] = kwargs[name]
            consumed_names.add(name)
            continue

        value = p.default
        if value is inspect.Parameter.empty:
            message = \
                "{}() missing required positional argument: '{}'".format(
                    self.code.co_name, p.name)
            raise TypeError(message)
        merged[name] = value

    if i < parameters_len and \
            parameters[i].kind == inspect.Parameter.VAR_POSITIONAL:
        p = parameters[i]
        i += 1

        merged[p.name] = args[consumed_i:]
    else:
        if consumed_i < len(args):
            raise TypeError(
                "{}() takes {} positional arguments but {} were given"
                .format(self.code.co_name, i, i + len(args) - consumed_i))

    while i < parameters_len and \
            parameters[i].kind == inspect.Parameter.KEYWORD_ONLY:
        p = parameters[i]
        i += 1

        name = p.name
        if name in kwargs:
            merged[name] = kwargs[name]
            consumed_names.add(name)
        elif p.default is not inspect.Parameter.empty:
            merged[name] = p.default
        else:
            raise TypeError(
                "{}() missing 1 required keyword-only argument: '{}'"
                .format(self.code.co_name, p.name))

    var_kws = {k: v for k, v in kwargs.items() if k not in consumed_names}
    if i < parameters_len and \
            parameters[i].kind == inspect.Parameter.VAR_KEYWORD:
        p = parameters[i]
        i += 1

        merged[p.name] = var_kws
    elif var_kws:
        raise TypeError(
            "{}() got multiple values for arguments '{}'".format(
                self.code.co_name, list(var_kws.keys())))

    return merged


def _identifier(self):
    return '.'.join((
        self.wrapped_callable.__module__, qualname(self.wrapped_callable)))


Callable.code = cached_property(_code)
Callable.annotations = property(_annotations)
Callable.kwargify = _kwargify
Callable.identifier = cached_property(_identifier)
