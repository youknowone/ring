
from __future__ import absolute_import

import re
from ring.tools import cached_property


try:
    unicode()
except NameError:
    unicode = str


class Key(object):

    def __init__(self, provider, indirect_marker='*'):
        self.provider = provider
        self.indirect_marker = indirect_marker

    def __repr__(self):
        return u'<{}.{} provider={}>'.format(
            self.__class__.__module__, self.__class__.__name__,
            self.provider)

    def build(self, args):
        raise NotImplementedError

    @cached_property
    def ordered_provider_keys(self):
        raise NotImplementedError

    @cached_property
    def provider_keys_set(self):
        return frozenset(self.ordered_provider_keys)

    def build_indirect_marker(self, args):
        full_args = {key: self.indirect_marker for key in self.provider_keys}
        full_args.update(args)
        return self.build(full_args)


class FormatKey(Key):

    def build(self, args):
        return self.provider.format(**args)

    @cached_property
    def ordered_provider_keys(self):
        keys = re.findall('{([a-zA-Z_][a-zA-Z_0-9]*)}', self.provider)
        return keys


class CallableKey(Key):

    def __init__(self, provider, indirect_marker='*', format_prefix=None, args_prefix_size=0, ignorable_keys=[]):
        assert callable(provider)
        super(CallableKey, self).__init__(provider, indirect_marker)
        self.args_prefix_size = args_prefix_size
        self.ignorable_keys = ignorable_keys
        if format_prefix is None:
            format_prefix = self.default_format_prefix
        if callable(format_prefix):
            format_prefix = format_prefix(provider)
        self.format = format_prefix + self.default_format_body(self.ordered_provider_keys)

    @cached_property
    def ordered_provider_keys(self):
        varnames = self.provider.__code__.co_varnames
        keys = varnames[self.args_prefix_size:]
        for key in self.ignorable_keys:
            if key not in self.ignorable_keys:
                raise KeyError(
                    "'{}' is not a varname but in ignorable_keys argument.".format(
                        key))
            del keys[keys.index(key)]
        return keys

    @staticmethod
    def default_format_prefix(provider):
        return '{}.{}'.format(provider.__module__, provider.__name__)

    @staticmethod
    def default_format_body(provider_keys):
        parts = []
        for key in provider_keys:
            parts.append(':{')
            parts.append(key)
            parts.append('}')
        return ''.join(parts)

    def merge_kwargs(self, args, kwargs):
        f_code = self.provider.__code__
        kwargs = kwargs.copy()
        for i, arg in enumerate(args[self.args_prefix_size:]):
            if i >= f_code.co_argcount:
                raise TypeError(
                    '{} takes {} positional arguments but {} were given'.format(
                        f_code.co_name, f_code.co_argcount, len(args)))
            varname = f_code.co_varnames[i]
            if varname in kwargs:
                raise TypeError(
                    "{}() got multiple values for argument '{}'".format(
                        f_code.co_name, varname))
            kwargs[varname] = arg
        for key in self.ignorable_keys:
            del kwargs[key]
        return kwargs

    def build(self, full_kwargs):
        return self.format.format(**full_kwargs)


def adapt_key(key):
    if isinstance(key, Key):
        return key
    if isinstance(key, (str, unicode)):
        return FormatKey(key)
    if callable(key):
        return CallableKey(key)
    raise TypeError
