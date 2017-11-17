
try:
    import ujson as json_mod
except ImportError:
    import json as json_mod

try:
    import pickle as pickle_mod
except ImportError:
    import cpickle as pickle_mod

class JsonCoder(object):

    @staticmethod
    def encode(data):
        return json_mod.dumps(data).encode('utf-8')

    @staticmethod
    def decode(binary):
        return json_mod.loads(binary.decode('utf-8'))


json = JsonCoder


class PickleCoder(object):

    @staticmethod
    def encode(data):
        return pickle_mod.dumps(data, 0)

    @staticmethod
    def decode(binary):
        return pickle_mod.loads(binary.decode('utf-8'))

pickle = PickleCoder
