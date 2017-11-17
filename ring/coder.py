
try:
    import ujson as json_mod
except ImportError:
    import json as json_mod


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
        return piclke_mod.dumps(data, 0)

    @staticmethod
    def decode(binary):
        return piclke_mod.loads(binary.decode('utf-8'))


pickle = PickleCoder

