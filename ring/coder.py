try:
    import ujson as json_mod
except ImportError:
    import json as json_mod

try:
    import pickle as piclke_mod
except ImportError:
    import cpickle as piclke_mod

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
        return piclke_mod.dumps(data).encode('utf-8')

    @staticmethod
    def decode(binary):
        return piclke_mod.loads(binary.decode('utf-8'))

pickle = PickleCoder

class registry(dict):
    def __init__(self):
        self = {}

    def register(self, key, value):
        self[key] = value
   
    def get(self, key):
        return self[key]

registry = registry()
registry.register('json', JsonCoder)
registry.register('pickle', PickleCoder)