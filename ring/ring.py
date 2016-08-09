
from __future__ import absolute_import

from .key import Key, FormatKey, CallableKey


def _build_func_key(f, args, kwargs):
    f_code = f.__code__
    for i, arg in enumerate(args):
        if i >= f_code.co_argcount:
            raise TypeError(
                '{} takes {} positional arguments but 4 were given'.format(
                    f_code.co_name, f_code.co_argcount, len(args)))
        varname = f_code.co_varnames[i]
        if varname in kwargs:
            raise TypeError(
                "{}() got multiple values for argument '{}'".format(
                    f_code.co_name, varname))
        kwargs[varname] = arg
    return kwargs


class Ring(object):

    def __init__(self, storage, key):
        self.storage = storage
        if not isinstance(key, Key):
            if isinstance(key, (str, unicode)):
                key = FormatKey(key)
            elif callable(key):
                key = CallableKey(key)
            else:
                raise TypeError
        self.key = key
        self.links = {}
        self.chains = {}

    def __call__(self, key=_build_func_key, expire=None):
        def _wrapper(f):
            def get_or_set(*args, **kwargs):
                built_args = key(f, args, kwargs)
                return self.get_or_set(f, **built_args)
            return get_or_set
        return _wrapper

    def get(self, **kwargs):
        return self.get_by_key(kwargs)

    def get_by_key(self, key_args):
        built_key = self.key.build(key_args)
        return self.storage.get(built_key)

    def delete(self, **kwargs):
        return self.delete_by_key(kwargs)

    def delete_by_key(self, key_args):
        built_key = self.key.build(key_args)
        return self.storage.delete(built_key)

    def set(self, _value, **kwargs):
        if callable(_value):
            _value = _value(**kwargs)
        return self.set_by_key(_value, kwargs)

    def set_by_key(self, value, key_args):
        built_key = self.key.build(key_args)
        return self.storage.set(built_key, value)

    def get_or_set(self, _value, **kwargs):
        value = self.get_by_key(kwargs)
        if value is None:
            value = _value(**kwargs)
            self.set_by_key(value, kwargs)
        return value

    def link(self, target, keys):
        self.links[target] = keys

    def chain(self, target, keys):
        self.chains[target] = keys
