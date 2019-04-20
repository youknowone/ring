""":mod:`ring.coder` --- Auto encode/decode layer
=================================================

Coder is a configurable layer that provides ways to encode raw data and decode
stored cache data.
"""
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

try:
    import dataclasses
except ImportError:
    dataclasses = None


@six.add_metaclass(abc.ABCMeta)
class Coder(object):
    """Abstract coder interface.

    See :func:`coderize` to create a Coder-compatible object in an easy way.
    See :class:`CoderTuple` to create a Coder-compatible object with functions.
    """

    @abc.abstractmethod
    def encode(self):  # pragma: no cover
        """Abstract encode function. Children must implement this function."""
        pass

    @abc.abstractmethod
    def decode(self):  # pragma: no cover
        """Abstract decode function. Children must implement this function."""
        pass


#: Coder-compatible tuple with encode and decode functions
CoderTuple = namedtuple('Coder', ['encode', 'decode'])
Coder.register(CoderTuple)


def coderize(raw_coder):
    if isinstance(raw_coder, Coder):
        coder = raw_coder
    else:
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
    """Coder registry.

    :see: :func:`ring.coder.registry` for default registry instance.
    """

    __slots__ = ('coders', )

    def __init__(self):
        self.coders = {}

    def register(self, coder_name, raw_coder):
        """Register `raw_coder` as a new coder with alias `coder_name`.

        Coder can be one of next types:

          - A :class:`Coder` subclass.
          - A :class:`CoderTuple` object.
          - A tuple of encode and decode functions.
          - An object which has encode and decode methods.

        :param str coder_name: A new coder name to register.
        :param object raw_coder: A new coder object.
        """
        coder = coderize(raw_coder)
        self.coders[coder_name] = coder

    def get(self, coder_name):
        """Get the registered coder for corresponding `coder_name`.

        This method is internally called when `coder` parameter is passed to
        ring object factory.
        """
        coder = self.coders.get(coder_name)
        return coder

    def get_or_coderize(self, raw_coder):
        coder = self.get(raw_coder)
        if coder is None:
            if isinstance(raw_coder, str):  # py2 support
                raise TypeError(
                    "The given coder is not a registered name in coder "
                    "registry.")
            coder = coderize(raw_coder)
        return coder


def bypass(x):
    return x


#: Default coder.
#:
#: encode and decode functions bypass the given parameter.
bypass_coder = bypass, bypass

#: Pickle coder.
#:
#: encode is :func:`pickle.dumps` and decode is :func:`pickle.loads`.
#: :mod:`cpickle` will be automatically loaded for CPython2.
pickle_coder = pickle_mod.dumps, pickle_mod.loads


class JsonCoder(Coder):
    """JSON Coder.

    When :mod:`ujson` package is installed, `ujson` is automatically selected;
    Otherwise, :mod:`json` will be used.
    """

    @staticmethod
    def encode(data):
        """Dump data to JSON string and encode it to UTF-8 bytes"""
        return json_mod.dumps(data).encode('utf-8')

    @staticmethod
    def decode(binary):
        """Decode UTF-8 bytes to JSON string and load it to object"""
        return json_mod.loads(binary.decode('utf-8'))


if dataclasses:
    class DataclassCoder(Coder):

        @staticmethod
        def encode(data):
            """Serialize dataclass object to json encoded dictionary"""
            target_dict = {
                'name': type(data).__name__,
                'fields': dataclasses.asdict(data)
            }
            return JsonCoder.encode(target_dict)

        @staticmethod
        def decode(binary):
            """Deserialize json encoded dictionary to dataclass object"""
            decoded_dict = JsonCoder.decode(binary)
            name = decoded_dict['name']
            fields = decoded_dict['fields']
            field_list = []
            for key, value in fields.items():
                field_list.append((key, type(value)))
            dataclass = dataclasses.make_dataclass(name, field_list)
            instance = dataclass(**fields)
            return instance

#: The default coder registry with pre-registered coders.
#: Built-in coders are registered by default.
#:
#: :see: :class:`ring.coder.Registry` for the class definition.
registry = Registry()
registry.register(None, bypass_coder)
registry.register('json', JsonCoder())
registry.register('pickle', pickle_coder)

if dataclasses:
    registry.register('dataclass', DataclassCoder())
