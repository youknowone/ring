from __future__ import absolute_import

import re
from ._util import cached_property
from .callable import Callable


class Key(object):

    def __init__(self, provider, indirect_marker='*'):
        self.provider = provider
        self.indirect_marker = indirect_marker

    def __repr__(self):
        return u'<{}.{} provider={}>'.format(
            type(self).__module__, type(self).__name__,
            self.provider)

    def build(self, args):  # pragma: no cover
        raise NotImplementedError

    def ordered_provider_keys(self):  # pragma: no cover
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

    def __init__(
            self, provider, indirect_marker='*', format_prefix=None,
            ignorable_keys=[], verbose=False):

        if not isinstance(provider, Callable):
            provider = Callable(provider)
        super(CallableKey, self).__init__(provider, indirect_marker)
        self.ignorable_keys = ignorable_keys
        if format_prefix is None:
            format_prefix = self.default_format_prefix
        if callable(format_prefix):
            format_prefix = format_prefix(provider)
        self.format = format_prefix + \
            self.default_format_body(
                self.ordered_provider_keys, verbose=verbose)

    @cached_property
    def ordered_provider_keys(self):
        keys = [arg.name for arg in self.provider.parameters_values]
        for key in self.ignorable_keys:
            if key not in keys:
                raise KeyError(
                    "'{}' is not an parameter name but in 'ignorable_keys'"
                    .format(key))
            keys.remove(key)
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
        merged = self.provider.kwargify(args, kwargs)
        for key in self.ignorable_keys:
            del merged[key]
        return merged

    def build(self, full_kwargs):
        # print(self.format, full_kwargs)
        key = self.format.format(**full_kwargs)
        return key
