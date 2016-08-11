
from __future__ import absolute_import

import re
from .tools import lazy_property


class Key(object):

    def __init__(self, key, indirect_marker='*'):
        self.key = key
        self.indirect_marker = indirect_marker

    def __repr__(self):
        return u'<{}.{} key={}>'.format(
            self.__class__.__module__, self.__class__.__name__,
            self.key)

    def build(self, args):
        raise NotImplementedError

    @lazy_property
    def partial_keys(self):
        raise NotImplementedError

    def build_indirect_marker(self, args):
        full_args = {key: self.indirect_marker for key in self.partial_keys}
        full_args.update(args)
        return self.build(full_args)


class FormatKey(Key):

    def build(self, args):
        return self.key.format(**args)

    @lazy_property
    def partial_keys(self):
        keys = re.findall('{([a-zA-Z_][a-zA-Z_0-9]*)}', self.key)
        return frozenset(keys)


class CallableKey(Key):

    def build(self, args):
        return self.key(**args)

    @lazy_property
    def partial_keys(self):
        code = self.key.__code__
        keys = code.co_varnames
        return frozenset(keys)
