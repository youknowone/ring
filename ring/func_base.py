""":mod:`ring.func_base` --- The building blocks of :mod:`ring.func`
====================================================================

"""
import abc
import functools
import types

import six
from ._compat import lru_cache, qualname
from .callable import Callable
from .key import CallableKey
from .wire import Wire
from .coder import registry as coder_registry, coderize

__all__ = (
    'is_method', 'is_classmethod', 'BaseRing', 'factory', 'NotFound',
    'BaseUserInterface', 'BaseStorage', 'CommonMixinStorage', )


@six.add_metaclass(abc.ABCMeta)
class BaseRing(object):
    """Abstract principal root class of Ring classes"""


def is_method(c):
    """Test given argument is a method or not.

    :param ring.callable.Callable c: A callable object.

    :note: The test is not based on python state but based on parameter name
           `self`. The test result might be wrong.
    """
    if not c.first_parameter:
        return False
    return c.first_parameter.name == 'self'


def is_classmethod(c):
    """Test given argument is a classmethod or not.

    :param ring.callable.Callable c: A callable object.
    """
    return isinstance(c.premitive, classmethod)


def suggest_ignorable_keys(c, ignorable_keys):
    if ignorable_keys is None:
        _ignorable_keys = []
    else:
        _ignorable_keys = ignorable_keys
    return _ignorable_keys


def suggest_key_prefix(c, key_prefix):
    if key_prefix is None:
        cc = c.callable
        if is_method(c):
            key_prefix = \
                '{0.__module__}.{{self.__class__.__qualname__}}.' \
                '{1}'.format(cc, qualname(cc))
            if not six.PY34:
                key_prefix = key_prefix.replace('__qualname__', '__name__')
        elif is_classmethod(c):
            # cls is already a str object somehow
            key_prefix = '{0.__module__}.{{cls}}.{1}'.format(
                cc, qualname(cc))
        else:
            key_prefix = '{0.__module__}.{1}'.format(
                cc, qualname(cc))
    else:
        key_prefix = key_prefix.replace('{', '{{').replace('}', '}}')
    return key_prefix


def _coerce_bypass(v):
    return v


def _coerce_list_and_tuple(v):
    return str(v).replace(' ', '')


def _coerce_type(v):
    return v.__name__


def _coerce_dict(v):
    return ','.join(['{},{}'.format(k, v[k]) for k in sorted(v.keys())])


def _coerce_set(v):
    return ','.join(sorted(v))


def _coerce_ring_key(v):
    return v.__ring_key__()


@lru_cache(maxsize=128)
def coerce_function(t):
    if hasattr(t, '__ring_key__'):
        return _coerce_ring_key

    if issubclass(t, (int, str, bool, type(None), type(Ellipsis))):
        return _coerce_bypass

    if issubclass(t, (list, tuple)):
        return _coerce_list_and_tuple

    if t == type:
        return _coerce_type

    if issubclass(t, dict):
        return _coerce_dict

    if issubclass(t, (set, frozenset)):
        return _coerce_set

    # NOTE: general sequence processing is good -
    # but NEVER add a general iterator processing. it will cause user bugs.


def coerce(v):
    """Transform the given value to cache-friendly string data."""
    type_coerce = coerce_function(type(v))
    if type_coerce:
        return type_coerce(v)

    if hasattr(v, '__ring_key__'):
        return v.__ring_key__()

    cls = v.__class__
    if cls.__str__ != object.__str__:
        return str(v)

    raise TypeError(
        "The given value '{}' of type '{}' is not a key-compatible type. "
        "Add __ring_key__() or __str__().".format(v, cls))


def create_ckey(c, key_prefix, ignorable_keys, coerce=coerce, encoding=None, key_refactor=lambda x: x):
    assert isinstance(c, Callable)
    ckey = CallableKey(
        c, format_prefix=key_prefix, ignorable_keys=ignorable_keys)

    def build_key(preargs, kwargs):
        full_kwargs = kwargs.copy()
        for i, prearg in enumerate(preargs):
            full_kwargs[c.parameters_values[i].name] = preargs[i]
        coerced_kwargs = {k: coerce(v) for k, v in full_kwargs.items() if k not in ignorable_keys}
        key = ckey.build(coerced_kwargs)
        if encoding:
            key = key.encode(encoding)
        key = key_refactor(key)
        return key

    ckey.build_key = build_key

    return ckey


def factory(
        storage_backend, key_prefix, on_manufactured,
        user_interface, storage_class, miss_value, expire_default, coder,
        default_action='get_or_update',
        ignorable_keys=None, key_encoding=None, key_refactor=lambda x: x):

    raw_coder = coder
    coder = coder_registry.get(raw_coder)
    if not coder:
        coder = coderize(raw_coder)

    def _decorator(f):
        cwrapper = Callable(f)
        _ignorable_keys = suggest_ignorable_keys(cwrapper, ignorable_keys)
        _key_prefix = suggest_key_prefix(cwrapper, key_prefix)
        ckey = create_ckey(
            cwrapper, _key_prefix, _ignorable_keys,
            encoding=key_encoding, key_refactor=key_refactor)

        class Ring(BaseRing):
            pass

        Ring.cwrapper = cwrapper
        Ring.ckey = ckey
        Ring.miss_value = miss_value
        Ring.expire_default = expire_default
        Ring.coder = coder

        class RingWire(Wire):

            def __init__(self, *args, **kwargs):
                super(RingWire, self).__init__(*args, **kwargs)
                ring = Ring()
                ring.wire = self
                ring.user_interface = user_interface(ring)
                ring.storage = storage_class(ring, storage_backend)
                ring.storage.backend = storage_backend
                self._ring = ring

                self.__func__ = ring.cwrapper.callable
                self.encode = ring.coder.encode
                self.decode = ring.coder.decode
                self.storage = ring.storage

            @functools.wraps(cwrapper.callable)
            def __call__(self, *args, **kwargs):
                return self.run(default_action, *args, **kwargs)

            def __getattr__(self, name):
                try:
                    return super(RingWire, self).__getattr__(name)
                except AttributeError:
                    pass
                try:
                    return self.__getattribute__(name)
                except AttributeError:
                    pass

                attr = getattr(self._ring.user_interface, name)
                if callable(attr):
                    function_args_count = getattr(
                        attr, '_function_args_count', 0)

                    def impl_f(*args, **kwargs):
                        full_kwargs = self.merge_args(
                            args[function_args_count:], kwargs)
                        function_args = args[:function_args_count]
                        return attr(*function_args, **full_kwargs)

                    c = self.cwrapper.callable
                    functools.wraps(c)(impl_f)
                    impl_f.__name__ = '.'.join((c.__name__, name))
                    if six.PY34:
                        impl_f.__qualname__ = '.'.join((c.__qualname__, name))

                    annotations = getattr(
                        impl_f, '__annotations__', {})
                    annotations_override = getattr(
                        attr, '__annotations_override__', {})
                    for field, override in annotations_override.items():
                        if isinstance(override, types.FunctionType):
                            new_annotation = override(annotations)
                        else:
                            new_annotation = override
                        annotations[field] = new_annotation

                    setattr(self, name, impl_f)

                return self.__getattribute__(name)

            def run(self, action, *args, **kwargs):
                attr = getattr(self, action)
                return attr(*args, **kwargs)

        wire = RingWire.for_callable(cwrapper)
        if on_manufactured is not None:
            on_manufactured(wire_frame=wire, ring_class=Ring)
        return wire

    return _decorator


class NotFound(Exception):
    """Internal exception for a cache miss.

    Ring internally use this exception to indicate a cache miss. Though common
    convention of cache miss is :data:`None` for many implementations,
    :mod:`ring.coder` allows :data:`None` to be proper cached value in
    **Ring**.
    """


class BaseStorage(object):
    """Base storage interface."""

    def __init__(self, ring, backend):
        self.ring = ring
        self.backend = backend

    @abc.abstractmethod
    def get(self, key):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def set(self, key, value, expire=Ellipsis):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, key):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def touch(self, key, expire=Ellipsis):  # pragma: no cover
        raise NotImplementedError


class CommonMixinStorage(BaseStorage):
    """General storage root for StorageMixin"""

    def get(self, key):
        value = self.get_value(key)
        return self.ring.coder.decode(value)

    def set(self, key, value, expire=Ellipsis):
        if expire is Ellipsis:
            expire = self.ring.expire_default
        encoded = self.ring.coder.encode(value)
        result = self.set_value(key, encoded, expire)
        return result

    def delete(self, key):
        result = self.delete_value(key)
        return result

    def touch(self, key, expire=Ellipsis):
        if expire is Ellipsis:
            expire = self.ring.expire_default
        result = self.touch_value(key, expire)
        return result


class StorageMixin(object):

    @abc.abstractmethod
    def get_value(self, key):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def set_value(self, key, value, expire):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def delete_value(self, key):  # pragma: no cover
        raise NotImplementedError

    def touch_value(self, key, expire):
        raise NotImplementedError


@six.add_metaclass(abc.ABCMeta)
class BaseUserInterface(object):

    def __init__(self, ring):
        self.ring = ring

    def key(self, **kwargs):
        args = self.ring.wire._preargs
        return self.ring.ckey.build_key(args, kwargs)
    key.__annotations_override__ = {
        'return': str,
    }

    def execute(self, **kwargs):
        return self.ring.cwrapper.callable(*self.ring.wire._preargs, **kwargs)

    def get(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def set(self, value, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def update(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def get_or_update(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def delete(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def touch(self, **kwargs):
        raise NotImplementedError
