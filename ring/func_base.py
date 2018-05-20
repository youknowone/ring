""":mod:`ring.func_base` --- The building blocks of :mod:`ring.func`
====================================================================

"""
import abc
import functools
import six
from ring._compat import lru_cache
from ring.callable import Callable
from ring.key import CallableKey
from ring.wire import Wire
from ring.coder import registry as coder_registry, coderize

__all__ = (
    'is_method', 'is_classmethod', 'RingBase', 'factory', 'NotFound',
    'StorageImplementation', 'BaseInterface')


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
        if is_method(c):
            key_prefix = \
                '{0.__module__}.{{self.__class__.__name__}}.' \
                '{0.__name__}'.format(c.callable)
        elif is_classmethod(c):
            # cls is already a str object somehow
            key_prefix = '{0.__module__}.{{cls}}.{0.__name__}'.format(c.callable)
        else:
            key_prefix = '{0.__module__}.{0.__name__}'.format(c.callable)
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


class RingBase(object):

    pass


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
        context, key_prefix, ring_factory,
        interface, storage_implementation, miss_value, expire_default, coder,
        ignorable_keys=None, key_encoding=None, key_refactor=lambda x: x):

    raw_coder = coder
    coder = coder_registry.get(raw_coder)
    if not coder:
        coder = coderize(raw_coder)

    def _decorator(f):
        _callable = Callable(f)
        _ignorable_keys = suggest_ignorable_keys(_callable, ignorable_keys)
        _key_prefix = suggest_key_prefix(_callable, key_prefix)
        ckey = create_ckey(
            _callable, _key_prefix, _ignorable_keys,
            encoding=key_encoding, key_refactor=key_refactor)

        ring = ring_factory(
            _callable, context, ckey, RingBase,
            interface, storage_implementation, miss_value, expire_default,
            coder)()

        class RingWire(Wire, interface):

            def __init__(self, *args, **kwargs):
                super(RingWire, self).__init__(*args, **kwargs)
                self.ring = ring
                self.ring.wire = self

            @functools.wraps(_callable.callable)
            def __call__(self, *args, **kwargs):
                return self.run('get_or_update', *args, **kwargs)

            def __getattr__(self, name):
                try:
                    return super(RingWire, self).__getattr__(name)
                except AttributeError:
                    pass
                try:
                    return self.__getattribute__(name)
                except AttributeError:
                    pass

                interface_name = '_' + name
                if hasattr(ring._interface_class, interface_name):
                    attr = self.__getattribute__(interface_name)
                    if callable(attr):
                        function_args_count = getattr(
                            attr, '_function_args_count', 0)

                        def impl_f(*args, **kwargs):
                            full_kwargs = self.merge_args(
                                args[function_args_count:], kwargs)
                            function_args = args[:function_args_count]
                            return attr(*function_args, **full_kwargs)

                        if function_args_count == 0:
                            functools.wraps(self._callable.callable)(impl_f)
                        setattr(self, name, impl_f)

                return self.__getattribute__(name)

        ring.wire = wire = RingWire.for_callable(_callable)
        wire._shared_attrs['ring'] = ring

        return wire

    return _decorator


class NotFound(Exception):
    """Internal exception for a cache miss.

    Ring internally use this exception to indicate a cache miss. Though common
    convention of cache miss is :data:`None` for many implementations,
    :mod:`ring.coder` allows :data:`None` to be proper cached value in
    **Ring**.
    """


@six.add_metaclass(abc.ABCMeta)
class StorageImplementation(object):

    @abc.abstractmethod
    def get_value(self, obj, key):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def set_value(self, obj, key, value, expire):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    def del_value(self, obj, key):  # pragma: no cover
        raise NotImplementedError

    def touch_value(self, obj, key, expire):
        raise NotImplementedError


@six.add_metaclass(abc.ABCMeta)
class BaseInterface(object):

    def _key(self, **kwargs):
        args = self._preargs
        return self.ring._ckey.build_key(args, kwargs)

    def _execute(self, **kwargs):
        return self.ring._p_execute(kwargs)

    def _get(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def _set(self, value, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def _update(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def _get_or_update(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def _delete(self, **kwargs):  # pragma: no cover
        raise NotImplementedError

    def _touch(self, **kwargs):
        raise NotImplementedError

    def run(self, action, *args, **kwargs):
        attr = getattr(self, action)
        return attr(*args, **kwargs)
