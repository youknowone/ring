import abc
import six
from collections import namedtuple
try:
    import ujson as json_mod
except ImportError:
    import json as json_mod

try:
    import cpickle as pickle_mod
except ImportError:
    import pickle as pickle_mod


@six.add_metaclass(abc.ABCMeta)
class Coder(object):
    @abc.abstractmethod
    def encode(self):
        pass

    @abc.abstractmethod
    def decode(self):
        pass


CoderTuple = namedtuple('Coder', ['encode', 'decode'])
Coder.register(CoderTuple)


def coderize(raw_coder):
    if isinstance(raw_coder, Coder):
        coder = raw_coder
    else:
        if isinstance(raw_coder, str):  # py2 support
            raise TypeError(
                "The given coder is not a registered name in coder registry.")
        if isinstance(raw_coder, tuple):
            coder = CoderTuple(*raw_coder)
        elif hasattr(raw_coder, 'encode') and hasattr(raw_coder, 'decode'):
            coder = CoderTuple(raw_coder.encode, raw_coder.decode)
        else:
            raise TypeError(
                "The given coder is not a coder compatibile object or "
                "not a registered name in coder registry")
    return coder


class Registry(object):

    __slots__ = ('coders', )

    def __init__(self):
        self.coders = {}

    def register(self, coder_name, raw_coder):
        coder = coderize(raw_coder)
        self.coders[coder_name] = coder

    def get(self, coder_name):
        coder = self.coders.get(coder_name)
        return coder


registry = Registry()


def bypass(x):
    return x


class JsonCoder(Coder):

    @staticmethod
    def encode(data):
        return json_mod.dumps(data).encode('utf-8')

    @staticmethod
    def decode(binary):
        return json_mod.loads(binary.decode('utf-8'))


registry.register(None, (bypass, bypass))
registry.register('json', JsonCoder())
registry.register('pickle', (pickle_mod.dumps, pickle_mod.loads))
