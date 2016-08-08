

class Storage(object):

    def get(self, key):
        raise NotImplementedError

    def set(self, key, value, expire=None):
        raise NotImplementedError


class DictStorage(Storage):

    def __init__(self, storage):
        self.storage = storage

    def get(self, key):
        return self.storage.get(key)

    def set(self, key, value, expire=None):
        assert expire is None, 'expire is not supported'
        return self.storage.update({key: value})
