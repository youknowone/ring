from __future__ import absolute_import

import collections
import types
import six
from ._util import cached_property
from ._compat import inspect, qualname

__all__ = ('Callable', )


_inspect_iscoroutinefunction = getattr(
    inspect, 'iscoroutinefunction', lambda f: False)


class Callable(object):
    """A wrapper object including more information of callables."""

    def __init__(self, f):
        self.wrapped_object = f
        if not callable(f):
            f = f.__func__
        self.wrapped_callable = f
        self.is_wrapped_coroutine = getattr(f, '_is_coroutine', None)
        self.is_coroutine = self.is_wrapped_coroutine or \
            _inspect_iscoroutinefunction(f)

    @cached_property
    def signature(self):
        return inspect.signature(self.wrapped_callable)

    @cached_property
    def parameters(self):
        return list(self.signature.parameters.values())

    @cached_property
    def code(self):
        """REAL __code__ for the given callable."""
        code_owner = self.wrapped_callable
        if self.is_wrapped_coroutine:
            code_owner = code_owner.__wrapped__
        return code_owner.__code__

    @property
    def annotations(self):
        return getattr(self.wrapped_callable, '__annotations__', None) or {}

    @cached_property
    def is_descriptor(self):
        return type(self.wrapped_object).__get__ is not types.FunctionType.__get__  # noqa

    @cached_property
    def is_barefunction(self):
        cc = self.wrapped_callable
        if six.PY34:
            method_name = cc.__qualname__.split('<locals>.')[-1]
            if method_name == cc.__name__:
                return True
            return False
        else:
            if self.is_descriptor:
                return False
            # im_class does not exist at this point
            return not (self.is_membermethod or self.is_classmethod)

    @cached_property
    def is_membermethod(self):
        """Test given argument is a method or not.

        :param ring.callable.Callable c: A callable object.
        :rtype: bool

        :note: The test is not based on python state but based on parameter
            name `self`. The test result might be wrong.
        """
        if six.PY34:
            if self.is_barefunction:
                return False
            if not self.is_descriptor:
                return True

        return self.first_parameter is not None \
            and self.first_parameter.name == 'self'

    @cached_property
    def is_classmethod(self):
        """Test given argument is a classmethod or not.

        :param ring.callable.Callable c: A callable object.
        :rtype: bool
        """
        if isinstance(self.wrapped_object, classmethod):
            return True
        if six.PY34:
            if self.is_barefunction:
                return False
            if not self.is_descriptor:
                return False

        return self.first_parameter is not None \
            and self.first_parameter.name == 'cls'

    def kwargify(self, args, kwargs, bound_args=()):
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

    @cached_property
    def identifier(self):
        return '.'.join((
            self.wrapped_callable.__module__, qualname(self.wrapped_callable)))

    @cached_property
    def first_parameter(self):
        parameters = self.parameters
        if not parameters:
            return None
        return parameters[0]
