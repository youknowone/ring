
from __future__ import absolute_import

import time
from collections import defaultdict
from .key import Key, FormatKey, CallableKey


try:
    unicode()
except NameError:
    unicode = str


class Link(object):

    def __init__(self, ring):
        self.ring = ring

    def __hash__(self):
        return hash(self.ring)

    def __eq__(self, other):
        return self.ring == other.ring

    def __repr__(self):
        return u'<{}.{} ring={}>'.format(
            self.__class__.__module__, self.__class__.__name__,
            self.ring)


class LinkDict(defaultdict):

    def link_items(self):
        for key, links in self.items():
            for link in links:
                yield key, link


class Ring(object):

    def __init__(self, storage, key, now=time.time):
        self.storage = storage
        if not isinstance(key, Key):
            if isinstance(key, (str, unicode)):
                key = FormatKey(key)
            elif callable(key):
                key = CallableKey(key)
            else:
                raise TypeError
        self.key = key
        self.func_now = now
        self.direct_links = LinkDict(set)
        self.indirect_links = LinkDict(set)
        self.incoming_links = LinkDict(set)

    def __repr__(self):
        return u'<{}.{} key={} storage={}>'.format(
            self.__class__.__module__, self.__class__.__name__,
            self.key, self.storage)

    def get(self, **kwargs):
        return self.get_by_key(kwargs)

    def has_indirect_marker(self, key_args, time):
        for partial_keys in self.incoming_links.keys():
            indirect_args = {key: key_args[key] for key in partial_keys}
            indirect_marker = self.key.build_indirect_marker(indirect_args)
            marked_time = self.storage.get(indirect_marker).time
            if marked_time is not None and marked_time > time:
                return True
        return False

    def get_by_key(self, key_args):
        built_key = self.key.build(key_args)
        result = self.storage.get(built_key)
        if result.time is None:
            return result.value
        if self.has_indirect_marker(key_args, result.time):
            # expire if it is marked indirectly
            self.storage.expire(built_key)
            return None
        return result.value

    def _mark_by_key(self, key_args):
        indirect_marker = self.key.build_indirect_marker(key_args)
        self.storage.update(indirect_marker, None, now=self.func_now())

    def expire(self, **kwargs):
        return self.expire_by_key(kwargs)

    def _chain_expire(self, key_args):
        for key, link in self.direct_links.link_items():
            link.ring.expire_by_key(key_args)
        for key, link in self.indirect_links.link_items():
            indirect_key_args = {k: v for k, v in key_args.items() if k in key}
            link.ring._mark_by_key(indirect_key_args)

    def expire_by_key(self, key_args):
        built_key = self.key.build(key_args)
        self.storage.expire(built_key)
        self._chain_expire(key_args)

    def update(self, _value, **kwargs):
        if callable(_value):
            _value = _value(**kwargs)
        return self.update_by_key(_value, kwargs)

    def update_by_key(self, value, key_args):
        built_key = self.key.build(key_args)
        self.storage.update(built_key, value, now=self.func_now())
        self._chain_expire(key_args)

    def get_or_update(self, _value, **kwargs):
        value = self.get_by_key(kwargs)
        if value is None:
            value = _value(**kwargs)
            self.update_by_key(value, kwargs)
        return value

    def link(self, target, keys=None):
        if keys is None:
            keys = self.key.partial_keys
        if not (keys >= target.key.partial_keys):
            raise TypeError(
                'Target has larger keys ({}) than given keys ({})'
                .format(target.key.partial_keys, keys))
        common_keys = target.key.partial_keys
        self.direct_links[common_keys].add(Link(target))

    def indirect_link(self, target, keys=None):
        if keys is None:
            keys = self.key.partial_keys
        common_keys = keys & target.key.partial_keys
        self.indirect_links[common_keys].add(Link(target))
        target.incoming_links[common_keys].add(Link(self))
        if keys >= target.key.partial_keys:
            raise TypeError(
                'Target has smaller keys. Direct links are recommended. '
                'Ignore this error to keep to use indirect links.')


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


class CallableRing(Ring):

    def __call__(self, key=_build_func_key, expire=None):
        def _wrapper(f):
            def get_or_update(*args, **kwargs):
                built_args = key(f, args, kwargs)
                return self.get_or_update(f, **built_args)
            return get_or_update
        return _wrapper
