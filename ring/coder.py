from collections import namedtuple
try:
    import ujson as json_mod
except ImportError:
    import json as json_mod

try:
    import cpickle as pickle_mod
except ImportError:
    import pickle as pickle_mod


Coder = namedtuple('Coder', ['encode', 'decode'])


class Registry(object):

    __slots__ = ('coders', )

    def __init__(self):
        self.coders = {}

    def register(self, coder_name, raw_coder):
        if isinstance(raw_coder, Coder):
            pass
        if not isinstance(raw_coder, tuple):
            raw_coder = raw_coder.encode, raw_coder.decode
        self.coders[coder_name] = Coder(raw_coder[0], raw_coder[1])

    def get(self, coder_name):
        coder = self.coders.get(coder_name)
        if not coder:
            raise TypeError(
                "'{}' is not a registered coder name.".format(coder_name))
        return coder


registry = Registry()


def bypass(x):
    return x


class JsonCoder(object):

    @staticmethod
    def encode(data):
        return json_mod.dumps(data).encode('utf-8')

    @staticmethod
    def decode(binary):
        return json_mod.loads(binary.decode('utf-8'))


registry.register(None, (bypass, bypass))
registry.register('json', JsonCoder())
registry.register('pickle', (pickle_mod.dumps, pickle_mod.loads))
