try:
    import ujson as json_mod
except ImportError:
    import json as json_mod

try:
    import cpickle as pickle_mod
except ImportError:
    import pickle as pickle_mod


class JsonCoder(object):

    @staticmethod
    def encode(data):
        return json_mod.dumps(data).encode('utf-8')

    @staticmethod
    def decode(binary):
        return json_mod.loads(binary.decode('utf-8'))


class PickleCoder(object):

    @staticmethod
    def encode(data):
        return pickle_mod.dumps(data)

    @staticmethod
    def decode(binary):
        return pickle_mod.loads(binary)


class Registry(object):

    def register(self, coder_name, coder):
        setattr(self, coder_name, coder)

    def get(self, coder_name):
        return getattr(self, coder_name, None)


registry = Registry()
