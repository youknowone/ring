""":mod:`ring.func_base` --- The building blocks of :mod:`ring.func`.
=====================================================================

"""
import abc
import functools
import types
from typing import List

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

    def compose_key(preargs, kwargs):
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

    return compose_key


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
    """Create a function for `transform_args` in interfaces' basic method.

    Each created function is called *transform function*. They are
    able to be passed as a value of `transform_args` parameter in
    :func:`ring.func_base.interface_attrs` decorator.

    The created transform function turns actual arguments of ring wires into
    uniform fully keyword-annotated arguments except for the first
    `prefix_count` number of positional arguments. So that the interface
    programmers can concentrate on the logic of the interface - not on the
    details of argument handling.

    :param int prefix_count: The number of prefix parameters. When it is
        a non-zero positive integer, the transform function will skip the
        first `prefix_count` number of positional arguments when it composes
        the fully keyword-annotated arguments. Use this to allow a method has
        the exact `prefix_count` number of additional *method parameters*.
    :return: A transform function with the given `prefix_count` option.

    :see: :class:`ring.func_base.BaseUserInterface` for usage.
    """
    def _wire_kwargs_only(wire, args, kwargs):
        wrapper_args = args[:prefix_count]
        function_args = args[prefix_count:]
        full_kwargs = wire.merge_args(function_args, kwargs)
        return wrapper_args, full_kwargs
    return _wire_kwargs_only


#: The single-access *transform_args* with 0 prefix parameter.
#: This function is created with :func:`ring.func_base.create_wire_kwargs_only`.
wire_kwargs_only0 = create_wire_kwargs_only(0)
#: The single-access *transform_args* with 1 prefix parameter.
#: This function is created with :func:`ring.func_base.create_wire_kwargs_only`.
wire_kwargs_only1 = create_wire_kwargs_only(1)


@six.add_metaclass(abc.ABCMeta)
class BaseUserInterface(object):
    """The base user interface class for single item access.

    An instance of interface class is bound to a **Ring** object. They have
    the one-to-one relationship. Subclass this class to create a new user
    interface. This is an abstract class. The methods marked as
    :func:`abc.abstractmethod` are mandatory; Otherwise not.

    This class provides sub-functions of ring wires. When trying to access
    any sub-function of a ring wire which doesn't exist, it looks up
    the composed user interface object and creates actual sub-function
    into the ring wire.

    The parameter *transform_args* in :func:`ring.func_base.interface_attrs`
    defines the figure of method parameters. For the base user interface,
    every method's *transform_args* is one of the results of
    :func:`ring.func_base.create_wire_kwargs_only`, e.g.
    :data:`ring.func_base.wire_kwargs_only0` or
    :data:`ring.func_base.wire_kwargs_only1`. Other mixins or subclasses may
    have different *transform_args*.

    The first parameter of interface method *always* is a **RingWire** object.
    The other parameters are composed by *transform_args*.

    :see: :func:`ring.func_base.create_wire_kwargs_only` for the specific
        argument transformation rule for each methods.

    The parameters below describe common methods' parameters.

    :param ring.func_base.factory...RingWire wire: The corresponding ring
        wire object.
    :param Dict[str,Any] kwargs: Fully keyword-annotated arguments. When
        actual function arguments are passed to each sub-function of the
        wire, they are merged as the form of keyword arguments. This gives
        the consistent interface for arguments handling. Note that it only
        describes the methods' *transform_args* attribute is the result of
        :func:`ring.func_base.create_wire_kwargs_only`
    """

    def __init__(self, ring):
        self.ring = ring

    @interface_attrs(transform_args=wire_kwargs_only0, return_annotation=str)
    def key(self, wire, **kwargs):
        """Create and return the composed key for storage.

        :see: The class documentation for the parameter details.
        :return: The composed key with given arguments.
        :rtype: str
        """
        args = wire._preargs
        return self.ring.compose_key(args, kwargs)

    @interface_attrs(transform_args=wire_kwargs_only0)
    def execute(self, wire, **kwargs):
        """Execute and return the result of original function.

        :see: The class documentation for the parameter details.
        :return: The result of the original function.
        """
        return self.ring.cwrapper.callable(*wire._preargs, **kwargs)

    @abc.abstractmethod
    @interface_attrs(transform_args=wire_kwargs_only0)
    def get(self, wire, **kwargs):  # pragma: no cover
        """Try to get and return the storage value of the corresponding key.

        :see: The class documentation for the parameter details.
        :see: :meth:`ring.func_base.BaseUserInterface.key` for the key.
        :return: The storage value for the corresponding key if it exists;
            Otherwise the `miss_value` of **Ring** object.
        """
        raise NotImplementedError

    @interface_attrs(transform_args=wire_kwargs_only1)
    def set(self, wire, value, **kwargs):  # pragma: no cover
        """Set the storage value of the corresponding key as the given `value`.

        :see: :meth:`ring.func_base.BaseUserInterface.key` for the key.

        :see: The class documentation for common parameter details.
        :param Any value: The value to save in the storage.
        :rtype: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    @interface_attrs(transform_args=wire_kwargs_only0)
    def update(self, wire, **kwargs):  # pragma: no cover
        """Execute the original function and `set` the result as the value.

        This action is comprehensible as a concatnation of
        :meth:`ring.func_base.BaseUserInterface.execute` and
        :meth:`ring.func_base.BaseUserInterface.set`.

        :see: :meth:`ring.func_base.BaseUserInterface.key` for the key.
        :see: :meth:`ring.func_base.BaseUserInterface.execute` for the
            execution.

        :see: The class documentation for the parameter details.
        :return: The result of the original function.
        """
        raise NotImplementedError

    @abc.abstractmethod
    @interface_attrs(transform_args=wire_kwargs_only0)
    def get_or_update(self, wire, **kwargs):  # pragma: no cover
        """Try to get and return the storage value; Otherwise, update and so.

        :see: :meth:`ring.func_base.BaseUserInterface.get` for get.
        :see: :meth:`ring.func_base.BaseUserInterface.update` for update.

        :see: The class documentation for the parameter details.
        :return: The storage value for the corresponding key if it exists;
            Otherwise result of the original function.
        """
        raise NotImplementedError

    @abc.abstractmethod
    @interface_attrs(transform_args=wire_kwargs_only0)
    def delete(self, wire, **kwargs):  # pragma: no cover
        """Delete the storage value of the corresponding key.

        :see: :meth:`ring.func_base.BaseUserInterface.key` for the key.

        :see: The class documentation for the parameter details.
        :rtype: None
        """
        raise NotImplementedError

    @interface_attrs(transform_args=wire_kwargs_only0)
    def has(self, wire, **kwargs):  # pragma: no cover
        """Return whether the storage has a value of the corresponding key.

        This is an optional function.

        :see: :meth:`ring.func_base.BaseUserInterface.key` for the key.

        :see: The class documentation for the parameter details.
        :return: Whether the storage has a value of the corresponding key.
        :rtype: bool
        """
        raise NotImplementedError

    @interface_attrs(transform_args=wire_kwargs_only0)
    def touch(self, wire, **kwargs):  # pragma: no cover
        """Touch the storage value of the corresponding key.

        This is an optional function.

        :note: `Touch` means resetting the expiration.
        :see: :meth:`ring.func_base.BaseUserInterface.key` for the key.

        :see: The class documentation for the parameter details.
        :rtype: bool
        """
        raise NotImplementedError


def create_bulk_key(interface, wire, args):
    if isinstance(args, tuple):
        kwargs = wire.merge_args(args, {})
        return interface.key(wire, **kwargs)
    elif isinstance(args, dict):
        return interface.key(wire, **args)
    else:
        raise TypeError(
            "Each parameter of '_many' suffixed sub-functions must be an "
            "instance of 'tuple' or 'dict'")


def execute_bulk_item(wire, args):
    if isinstance(args, tuple):
        return wire._ring.cwrapper.callable(*(wire._preargs + args))
    elif isinstance(args, dict):
        return wire._ring.cwrapper.callable(*wire._preargs, **args)
    else:
        raise TypeError(
            "Each parameter of '_many' suffixed sub-functions must be an "
            "instance of 'tuple' or 'dict'")


class AbstractBulkUserInterfaceMixin(object):
    """Bulk access interface mixin.

    Every method in this mixin is optional. The methods have each
    corresponding function in :class:`ring.func_base.BaseUserInterface`.

    The parameters below describe common methods' parameters.

    :param ring.func_base.factory...RingWire wire: The corresponding ring
        wire object.
    :param Iterable[Union[tuple,dict]] args_list: A sequence of arguments of
        the original function. While **args_list** is a list of **args**,
        each **args** (:class:`Union[tuple,dict]`) is a complete set of
        positional-only formed or keyword-only formed arguments.
        When the **args** (:class:`tuple`) is positional-only formed, its type
        must be always :class:`tuple`. Any other iterable types like `list`
        are not allowed. When any keyword-only argument is required, use
        keyword-only formed arguments.
        When the **args** (:class:`dict`) is keyword-only formed, its type must
        be always :class:`dict`. When there is a variant positional argument,
        pass the values them as a :class:`tuple` of parameters with the
        corresponding variant positional parameter name.
        The restriction gives the simple and consistent interface for
        multiple dispatching. Note that it only describes the methods which
        don't have *transform_args* attribute.
    """

    @interface_attrs(return_annotation=lambda a: List[str])
    def key_many(self, wire, *args_list):
        """Create and return the composed keys for storage.

        :see: The class documentation for the parameter details.
        :return: A sequence of created keys.
        :rtype: Sequence[str]
        """
        return [create_bulk_key(self, wire, args) for args in args_list]

    def execute_many(self, wire, *args_list):  # pragma: no cover
        """Execute and return the results of the original function.

        :see: The class documentation for the parameter details.
        :return: A sequence of the results of the original function.
        :rtype: Sequence of the return type of the original function
        """
        raise NotImplementedError

    def get_many(self, wire, *args_list):  # pragma: no cover
        """Try to get and returns the storage values.

        :see: The class documentation for the parameter details.
        :return: A sequence of the storage values or `miss_value` for the
            corresponding keys. When a key exists in the storage, the matching
            value is selected; Otherwise the `miss_value` of **Ring** object
            is.
        """
        raise NotImplementedError

    def update_many(self, wire, *args_list):  # pragma: no cover
        """Execute the original function and `set` the result as the value.

        :see: The class documentation for the parameter details.
        :return: A sequence of the results of the original function.
        :rtype: Sequence of the return type of the original function
        """
        raise NotImplementedError

    def get_or_update_many(self, wire, *args_list):  # pragma: no cover
        """Try to get and returns the storage values.

        :note: The semantic of this function may vary by the implementation.
        :see: The class documentation for the parameter details.
        :return: A sequence of the storage values or the exceuted result of the
            original function for the corresponding keys. When a key exists
            in the storage, the matching value is selected; Otherwise the
            result of the original function is.
        """
        raise NotImplementedError

    def set_many(self, wire, args_list, value_list):  # pragma: no cover
        """Set the storage values of the corresponding keys as the given values.

        :see: The class documentation for common parameter details.
        :param Iterable[Any] value_list: A list of the values to save in
            the storage.
        :rtype: None
        """
        raise NotImplementedError

    def delete_many(self, wire, *args_list):  # pragma: no cover
        """Delete the storage values of the corresponding keys.

        :see: The class documentation for the parameter details.
        :rtype: None
        """
        raise NotImplementedError

    def has_many(self, wire, *args_list):  # pragma: no cover
        """Return whether the storage has values of the corresponding keys.

        :see: The class documentation for the parameter details.
        :rtype: Sequence[bool]
        """
        raise NotImplementedError

    def touch_many(self, wire, *args_list):  # pragma: no cover
        """Touch the storage values of the corresponding keys.

        :see: The class documentation for the parameter details.
        :rtype: None
        """
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
        user_interface = type('_ComposedUserInterface', user_interface, {})

    def _decorator(f):
        cw = Callable(f)
        _ignorable_keys = suggest_ignorable_keys(cw, ignorable_keys)
        _key_prefix = suggest_key_prefix(cw, key_prefix)
        key_builder = create_key_builder(
            cw, _key_prefix, _ignorable_keys,
            encoding=key_encoding, key_refactor=key_refactor)

        class RingCore(BaseRing):
            cwrapper = cw
            compose_key = staticmethod(key_builder)

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
    convention of the cache miss is :data:`None` for many implementations,
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
        """Get actual data by given key."""
        raise NotImplementedError

    @abc.abstractmethod
    def set(self, key, value, expire=Ellipsis):  # pragma: no cover
        """Set actual data by given key, value and expire."""
        raise NotImplementedError

    @abc.abstractmethod
    def delete(self, key):  # pragma: no cover
        """Delete data by given key."""
        raise NotImplementedError

    @abc.abstractmethod
    def touch(self, key, expire=Ellipsis):  # pragma: no cover
        """Touch data by given key."""
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

    def has(self, key):
        result = self.has_value(key)
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
        """Get and return value for the given key."""
        raise NotImplementedError

    @abc.abstractmethod
    def set_value(self, key, value, expire):  # pragma: no cover
        """Set value for the given key, value and expire."""
        raise NotImplementedError

    @abc.abstractmethod
    def delete_value(self, key):  # pragma: no cover
        """Delete value for the given key."""
        raise NotImplementedError

    def has_value(self, key):
        """Check and return data existences for the given key. (optional)"""
        raise AttributeError

    def touch_value(self, key, expire):
        """Touch value for the given key. (optional)"""
        raise AttributeError
