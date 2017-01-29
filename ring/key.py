
from __future__ import absolute_import

import re
from ring.util import cached_property


try:
    unicode()
    py3 = False
except NameError:
    unicode = str
    py3 = True


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


class CallableWrapper(object):
    def __init__(self, c):
        assert callable(c)
        self.callable = c

    @cached_property
    def identifier(self):
        return '{self.callable.__module__}.{self.callable.__name__}'.format(
            self=self)

    @cached_property
    def code(self):
        c = self.callable
        if hasattr(c, '_is_coroutine'):
            code = c.__wrapped__.__code__
        else:
            code = c.__code__
        return code

    @cached_property
    def varnames(self):
        code = self.code
        arg_count = code.co_argcount
        if py3:
            arg_count += code.co_kwonlyargcount
        return code.co_varnames[:arg_count]

    @cached_property
    def first_varname(self):
        if not self.code.co_varnames:
            return None
        return self.code.co_varnames[0]


class CallableKey(Key):

    def __init__(self, provider, indirect_marker='*', format_prefix=None, ignorable_keys=[], verbose=False):
        if not isinstance(provider, CallableWrapper):
            provider = CallableWrapper(provider)
        super(CallableKey, self).__init__(provider, indirect_marker)
        self.ignorable_keys = ignorable_keys
        if format_prefix is None:
            format_prefix = self.default_format_prefix
        if callable(format_prefix):
            format_prefix = format_prefix(provider)
        self.format = format_prefix + self.default_format_body(self.ordered_provider_keys, verbose=verbose)

    @cached_property
    def ordered_provider_keys(self):
        varnames = self.provider.varnames
        keys = list(varnames)
        for key in self.ignorable_keys:
            if key not in self.ignorable_keys:
                raise KeyError(
                    "'{}' is not a varname but in ignorable_keys argument.".format(
                        key))
            del keys[keys.index(key)]
        return keys

    @staticmethod
    def default_format_prefix(provider):
        return provider.identifier

    @staticmethod
    def default_format_body(provider_keys, verbose):
        parts = []
        for key in provider_keys:
            if verbose:
                parts.append(':{key}={{{key}}}'.format(key=key))
            else:
                parts.append(':{{{key}}}'.format(key=key))
        return ''.join(parts)

    def merge_kwargs(self, args, kwargs):
        f_code = self.provider.code
        kwargs = kwargs.copy()
        for i, arg in enumerate(args):
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
        # print(self.format, full_kwargs)
        key = self.format.format(**full_kwargs)
        return key
