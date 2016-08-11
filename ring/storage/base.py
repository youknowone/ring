
from __future__ import absolute_import
from collections import namedtuple


class BaseStorage(object):

    def get(self, key, now=None):
        raise NotImplementedError

    def update(self, key, value, expire=None, now=None):
        raise NotImplementedError

    def expire(self, key, now=None):
        raise NotImplementedError


StorageReturn = namedtuple('StorageReturn', ['time', 'value'])


class DictStorage(BaseStorage):

    def __init__(self, backend):
        self.backend = backend

    def get(self, key, now=None):
        value = self.backend.get(key)
        if value is None:
            return StorageReturn(None, None)
        else:
            return StorageReturn(*value)

    def update(self, key, value, expire=None, now=None):
        assert expire is None, 'expire is not supported'
        return self.backend.update({key: (now, value)})

    def expire(self, key):
        return self.backend.pop(key, None)
