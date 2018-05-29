""":mod:`ring.func_base` --- The building blocks of :mod:`ring.func`.
=====================================================================

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
    'BaseUserInterface', 'BaseStorage', 'CommonMixinStorage', 'StorageMixin')


@six.add_metaclass(abc.ABCMeta)
class BaseRing(object):
    """Abstract principal root class of Ring classes."""


def is_method(c):
    """Test given argument is a method or not.

    :param ring.callable.Callable c: A callable object.
    :rtype: bool

    :note: The test is not based on python state but based on parameter name
           `self`. The test result might be wrong.
    """
    if not c.first_parameter:
        return False
    return c.first_parameter.name == 'self'


def is_classmethod(c):
    """Test given argument is a classmethod or not.

    :param ring.callable.Callable c: A callable object.
    :rtype: bool
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


def create_key_builder(
        c, key_prefix, ignorable_keys, coerce=coerce, encoding=None,
        key_refactor=None):
    assert isinstance(c, Callable)
    key_generator = CallableKey(
        c, format_prefix=key_prefix, ignorable_keys=ignorable_keys)

    def build_key(preargs, kwargs):
        full_kwargs = kwargs.copy()
        for i, prearg in enumerate(preargs):
            full_kwargs[c.parameters_values[i].name] = preargs[i]
        coerced_kwargs = {
            k: coerce(v) for k, v in full_kwargs.items() if k not in ignorable_keys}
        key = key_generator.build(coerced_kwargs)
        if encoding:
            key = key.encode(encoding)
        if key_refactor:
            key = key_refactor(key)
        return key

    return build_key


def interface_attrs(**kwargs):
    if 'return_annotation' in kwargs:
        kwargs['__annotations_override__'] = {
            'return': kwargs.pop('return_annotation')}

    assert frozenset(kwargs.keys()) <= frozenset(
        {'transform_args', '__annotations_override__'})

    def _decorator(f):
        f.__dict__.update(kwargs)
        return f

    return _decorator


def create_wire_kwargs_only(prefix_count=0):
    def _wire_kwargs_only(wire, args, kwargs):
        wrapper_args = args[:prefix_count]
        function_args = args[prefix_count:]
        full_kwargs = wire.merge_args(function_args, kwargs)
        return wrapper_args, full_kwargs
    return _wire_kwargs_only


wire_kwargs_only0 = create_wire_kwargs_only(0)
wire_kwargs_only1 = create_wire_kwargs_only(1)


@six.add_metaclass(abc.ABCMeta)
class BaseUserInterface(object):
    """Abstract user interface.

    This class provides sub-functions of ring wire. When trying to access
    any sub-function of a ring wire which doesn't exist, it looks up
    the composited user interface object and creates actual sub-function
    into the ring wire.

    Subclass this class to create a new user interface. The methods marked
    as :func:`abc.abstractmethod` are mandatory; Otherwise not.
    """

    def __init__(self, ring):
        self.ring = ring

    @interface_attrs(transform_args=wire_kwargs_only0, return_annotation=str)
    def key(self, wire, **kwargs):
        args = wire._preargs
        return self.ring.build_key(args, kwargs)

    @interface_attrs(transform_args=wire_kwargs_only0)
    def execute(self, wire, **kwargs):
        return self.ring.cwrapper.callable(*wire._preargs, **kwargs)

    @abc.abstractmethod
    @interface_attrs(transform_args=wire_kwargs_only0)
    def get(self, wire, **kwargs):  # pragma: no cover
        raise NotImplementedError

    @interface_attrs(transform_args=wire_kwargs_only1)
    def set(self, wire, value, **kwargs):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    @interface_attrs(transform_args=wire_kwargs_only0)
    def update(self, wire, **kwargs):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    @interface_attrs(transform_args=wire_kwargs_only0)
    def get_or_update(self, wire, **kwargs):  # pragma: no cover
        raise NotImplementedError

    @abc.abstractmethod
    @interface_attrs(transform_args=wire_kwargs_only0)
    def delete(self, wire, **kwargs):  # pragma: no cover
        raise NotImplementedError

    @interface_attrs(transform_args=wire_kwargs_only0)
    def touch(self, wire, **kwargs):
        raise NotImplementedError


def factory(
        storage_backend,  # actual storage
        key_prefix,  # manual key prefix
        expire_default,  # default expiration
        # building blocks
        coder, miss_value, user_interface, storage_class,
        default_action='get_or_update',
        # callback
        on_manufactured=None,
        # key builder related parameters
        ignorable_keys=None, key_encoding=None, key_refactor=None):
    """Create a decorator which turns a function into ring wire or wire bridge.

    This is the base factory function that every internal **Ring** factories
    are based on. See the source code of :mod:`ring.func_sync` or
    :mod:`ring.func_asyncio` for actual usages and sample code.

    :param Any storage_backend: Actual storage backend instance.
    :param Optional[str] key_prefix: Specify storage key prefix when a
        :class:`str` value is given; Otherwise a key prefix is automatically
        suggested based on the function signature. Note that the suggested
        key prefix is not compatible between Python 2 and 3.
    :param Optional[float] expire_default: Set the duration of seconds to
        expire the data when a number is given; Otherwise the default
        behavior depends on the backend. Note that the storage may or may
        not support expiration or persistent saving.

    :param Union[str,ring.coder.Coder] coder: A registered coder name or a
        coder object. See :doc:`coder` for details.
    :param Any miss_value: The default value when storage misses a given key.
    :param type user_interface: Injective implementation of sub-functions.
    :param type storage_class: Injective implementation of storage.
    :param Optional[str] default_action: The default action name for
        `__call__` of the wire object. When the given value is :data:`None`,
        there is no `__call__` method for ring wire.

    :param Optional[Callable[[type(Wire),type(Ring)],None]] on_manufactured:
        The callback function when a new ring wire or wire bridge is created.

    :param List[str] ignorable_keys: (experimental) Parameter names not to
        use to create storage key.
    :param Optional[str] key_encoding: The storage key is usually
        :class:`str` typed. When this parameter is given, a key is encoded
        into :class:`bytes` using the given encoding.
    :param Optional[Callable[[str],str]] key_refactor: Roughly,
        ``key = key_refector(key)`` will be run when `key_refector` is not
        :data:`None`; Otherwise it is omitted.

    :return: The factory decorator to create new ring wire or wire bridge.
    :rtype: (Callable)->Union[ring.wire.Wire,ring.wire.WiredProperty]
    """
    raw_coder = coder
    coder = coder_registry.get(raw_coder)
    if not coder:
        coder = coderize(raw_coder)

    if isinstance(user_interface, (tuple, list)):
        class _UserInterface(*user_interface):
            pass
        user_interface = _UserInterface

    def _decorator(f):
        cw = Callable(f)
        _ignorable_keys = suggest_ignorable_keys(cw, ignorable_keys)
        _key_prefix = suggest_key_prefix(cw, key_prefix)
        key_builder = create_key_builder(
            cw, _key_prefix, _ignorable_keys,
            encoding=key_encoding, key_refactor=key_refactor)

        class RingCore(BaseRing):
            cwrapper = cw
            build_key = staticmethod(key_builder)

            def __init__(self):
                super(BaseRing, self).__init__()
                self.user_interface = user_interface(self)
                self.storage = storage_class(self, storage_backend)

        RingCore.miss_value = miss_value
        RingCore.expire_default = expire_default
        RingCore.coder = coder

        ring = RingCore()

        class RingWire(Wire):

            def __init__(self, *args, **kwargs):
                super(RingWire, self).__init__(*args, **kwargs)
                self._ring = ring

                self.__func__ = ring.cwrapper.callable
                self.encode = ring.coder.encode
                self.decode = ring.coder.decode
                self.storage = ring.storage

            if default_action is not None:
                @functools.wraps(ring.cwrapper.callable)
                def __call__(self, *args, **kwargs):
                    return self.run(default_action, *args, **kwargs)
            else:  # Empty block to test coverage
                pass

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
                    transform_args = getattr(
                        attr, 'transform_args', None)

                    def impl_f(*args, **kwargs):
                        if transform_args:
                            args, kwargs = transform_args(self, args, kwargs)
                        return attr(self, *args, **kwargs)

                    c = self._ring.cwrapper.callable
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

        wire = RingWire.for_callable(ring.cwrapper)
        if on_manufactured is not None:
            on_manufactured(wire_frame=wire, ring=ring)

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
    """Base storage interface.

    To add a new storage interface, regard to use
    :class:`ring.func_base.CommonMixinStorage` and a subclass of
    :class:`ring.func_base.StorageMixin`.

    When subclassing this interface, remember `get` and `set` methods must
    include coder works. The methods marked as :func:`abc.abstractmethod`
    are mandatory; Otherwise not.
    """

    def __init__(self, ring, backend):
        self.ring = ring
        self.backend = backend

    @abc.abstractmethod
    def get(self, key):  # pragma: no cover
        """Get actual data by given key.

        :param str key: Storage key.
        :return: Decoded data of the given key.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set(self, key, value, expire=Ellipsis):  # pragma: no cover
        """Set actual data by given key, value and expire.

        :param str key: Storage key.
        :param Any value: The value to save to the given key.
        :param float expire: Expiration duration in seconds.
        :rtype: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, key):  # pragma: no cover
        """Delete data by given key.

        :param str key: Storage key.
        :rtype: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def touch(self, key, expire=Ellipsis):  # pragma: no cover
        """Touch data by given key.

        :param str key: Storage key.
        :param float expire: Expiration duration in seconds.
        :rtype: None
        """
        raise NotImplementedError


class CommonMixinStorage(BaseStorage):
    """General storage root for StorageMixin."""

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
    """Abstract storage mixin class.

    Subclass this class to create a new storage mixin. The methods marked
    as :func:`abc.abstractmethod` are mandatory; Otherwise not.
    """

    @abc.abstractmethod
    def get_value(self, key):  # pragma: no cover
        """Get value by given key.

        :param str key: Storage key.
        :rtype: :class:`bytes` is recommended.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def set_value(self, key, value, expire):  # pragma: no cover
        """Set value by given key, value and expire.

        :param str key: Storage key.
        :param bytes value: :class:`bytes` is recommended.
        :param Optional[float] expire: Expiration duration in seconds.
        :rtype: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_value(self, key):  # pragma: no cover
        """Delete value by given key.

        :param str key: Storage key.
        :rtype: None
        """
        raise NotImplementedError

    def touch_value(self, key, expire):
        """Touch value by given key.

        :param str key: Storage key.
        :rtype: None
        """
        raise NotImplementedError
