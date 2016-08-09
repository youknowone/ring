
from __future__ import absolute_import

import re
from .tools import lazy_property


class Key(object):

    def __init__(self, key):
        self.key = key

    def build(self, args):
        raise NotImplementedError

    @lazy_property
    def partial_keys(self):
        raise NotImplementedError


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
