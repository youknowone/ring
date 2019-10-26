""":mod:`ring.func.base` --- The building blocks of **ring.func.\***.
=====================================================================

"""  # noqa: W605
import abc
import types
from typing import List

import attr
import six
from wirerope import Wire, WireRope, RopeCore
from .._compat import functools, qualname
from ..callable import Callable
from ..key import CallableKey
from ..coder import registry as default_registry
from .._util import cached_property

try:
    import numpy
except ImportError:
    numpy = None

try:
    import dataclasses
    import contextvars
except ImportError:  # pragma: no cover
    contextvars = None
    dataclasses = None

__all__ = (
    'factory', 'NotFound',
    'BaseUserInterface', 'BaseStorage', 'CommonMixinStorage', 'StorageMixin')


def suggest_ignorable_keys(c, ignorable_keys):
    if ignorable_keys is None:
        _ignorable_keys = []
    else:
        _ignorable_keys = ignorable_keys
    return _ignorable_keys


def suggest_key_prefix(c, key_prefix):
    if key_prefix is None:
        key_prefix = c.identifier
        if six.PY2:
            cc = c.wrapped_callable
            # A proper solution is `im_class` of the bound method
            if c.is_membermethod:
                key_prefix = \
                    '{0.__module__}.{{self.__class__.__name__}}.{0.__name__}' \
                    .format(cc)
            elif c.is_classmethod:
                key_prefix = '{0.__module__}.{{cls}}.{0.__name__}'.format(cc)
    else:
        key_prefix = key_prefix.replace('{', '{{').replace('}', '}}')
    return key_prefix


def _coerce_bypass(v):
    return v


def _coerce_ndarray(v):
    return "{}:{}".format(type(v).__name__, str(v).replace(' ', ','))


def _coerce_list_and_tuple(v):
    return str(v).replace(' ', '')


def _coerce_type(v):
    return v.__name__


def _coerce_dict(v):
    return ','.join(['{},{}'.format(k, v[k]) for k in sorted(v.keys())])


def _coerce_set(v):
    elements = ','.join([
        "'{}'".format(e) if isinstance(e, str) else str(e)
        for e in sorted(v)
    ])
    return "{" + "{}".format(elements) + "}"


def _coerce_ring_key(v):
    return v.__ring_key__()


def _coerce_dataclass(v):
    return type(v).__name__ + _coerce_dict(dataclasses.asdict(v))


@functools.lru_cache(maxsize=128)
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

    if numpy:
        if issubclass(t, numpy.ndarray):
            return _coerce_ndarray

    if dataclasses:
        if dataclasses.is_dataclass(t):
            return _coerce_dataclass

    # NOTE: general sequence processing is good -
    # but NEVER add a general iterator processing. it will cause user bugs.


def coerce(v, in_memory_storage):
    """Transform the given value to cache-friendly string data."""

    type_coerce = coerce_function(type(v))
    if type_coerce:
        return type_coerce(v)

    if hasattr(v, '__ring_key__'):
        return v.__ring_key__()

    if in_memory_storage and type(v).__hash__ != object.__hash__:
        return "{}:hash:{}".format(qualname(type(v)), hash(v))

    cls = type(v)
    if cls.__str__ != object.__str__:
        return str(v)

    msg = "Add __ring_key__() or __str__()."
    if in_memory_storage:
        msg = "Add __ring_key__(), __str__() or __hash__()."

    raise TypeError(
        "The given value '{}' of type '{}' is not a key-compatible type. {}".format(v, cls, msg))


def create_key_builder(
        c, key_prefix, ignorable_keys, coerce=coerce, encoding=None,
        key_refactor=None, in_memory_storage=False):
    assert isinstance(c, Callable)
    key_generator = CallableKey(
        c, format_prefix=key_prefix, ignorable_keys=ignorable_keys)

    def compose_key(*bound_args, **kwargs):
        full_kwargs = kwargs.copy()
        for i, prearg in enumerate(bound_args):
            full_kwargs[c.parameters[i].name] = bound_args[i]
        coerced_kwargs = {
            k: coerce(v, in_memory_storage) for k, v in full_kwargs.items()
            if k not in ignorable_keys}
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

    if 'transform_args' in kwargs:
        transform_args = kwargs.pop('transform_args')
        if transform_args:
            if type(transform_args) != tuple:
                transform_args = transform_args, {}
            func, rules = transform_args
            assert frozenset(rules.keys()) <= frozenset({'prefix_count'})
            kwargs['transform_args'] = transform_args

    assert frozenset(kwargs.keys()) <= frozenset(
        {'transform_args', '__annotations_override__'})

    def _decorator(f):
        f.__dict__.update(kwargs)
        return f

    return _decorator


def transform_kwargs_only(wire, rules, args, kwargs):
    """`transform_args` for basic single-access methods in interfaces.

    Create and returns uniform fully keyword-annotated arguments except for
    the first ``rule.get('prefix_count')`` number of positional arguments for
    given actual arguments of ring wires. So that the interface programmers
    can concentrate on the logic of the interface - not on the details of
    argument handling.

    This function is the argument of `transform_args` parameter of
    :func:`ring.func.base.interface_attrs` decorator for ordinary
    single-access methods.

    :param int rules.prefix_count: The number of prefix parameters. When it is
        a positive integer, the transform function will skip the
        first `prefix_count` number of positional arguments when it composes
        the fully keyword-annotated arguments. Use this to allow a method has
        the exact `prefix_count` number of additional *method parameters*.
        The default value is ``0``.
    :return: The fully keyword-annotated arguments.
    :rtype: dict

    :see: the source code of :class:`ring.func.base.BaseUserInterface` about
        actual usage.
    """
    prefix_count = rules.get('prefix_count', 0)
    wrapper_args = args[:prefix_count]
    function_args = args[prefix_count:]
    full_kwargs = wire._merge_args(function_args, kwargs)
    return wrapper_args, full_kwargs


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

    The parameter *transform_args* in :func:`ring.func.base.interface_attrs`
    defines the figure of method parameters. For the **BaseUserInterface**,
    every method's *transform_args* is
    :func:`ring.func.base.transform_kwargs_only` which force to pass uniform
    keyword arguments to the interface methods.
    Other mix-ins or subclasses may have different *transform_args*.

    The first parameter of interface method *always* is a **RingWire** object.
    The other parameters are composed by *transform_args*.

    :see: :func:`ring.func.base.transform_kwargs_only` for the specific
        argument transformation rule for each methods.

    The parameters below describe common methods' parameters.

    :param ring.func.base.RingWire wire: The corresponding ring
        wire object.
    :param Dict[str,Any] kwargs: Fully keyword-annotated arguments. When
        actual function arguments are passed to each sub-function of the
        wire, they are merged into the form of keyword arguments. This gives
        the consistent interface for arguments handling. Note that it only
        describes the methods' *transform_args* attribute is
        :func:`ring.func.base.transform_kwargs_only`
    """

    def __init__(self, ring):
        self._ring = ring

    @interface_attrs(
        transform_args=transform_kwargs_only, return_annotation=str)
    def key(self, wire, **kwargs):
        """Create and return the composed key for storage.

        :see: The class documentation for the parameter details.
        :return: The composed key with given arguments.
        :rtype: str
        """
        return wire._rope.compose_key(*wire._bound_objects, **kwargs)

    @interface_attrs(transform_args=transform_kwargs_only)
    def execute(self, wire, **kwargs):
        """Execute and return the result of the original function.

        :see: The class documentation for the parameter details.
        :return: The result of the original function.
        """
        return wire.__func__(**kwargs)

    @abc.abstractmethod
    @interface_attrs(transform_args=transform_kwargs_only)
    def get(self, wire, **kwargs):  # pragma: no cover
        """Try to get and return the storage value of the corresponding key.

        :see: The class documentation for the parameter details.
        :see: :meth:`ring.func.base.BaseUserInterface.key` for the key.
        :return: The storage value for the corresponding key if it exists;
            Otherwise, the `miss_value` of **Ring** object.
        """
        raise NotImplementedError

    @interface_attrs(
        transform_args=(transform_kwargs_only, {'prefix_count': 1}))
    def set(self, wire, value, **kwargs):  # pragma: no cover
        """Set the storage value of the corresponding key as the given `value`.

        :see: :meth:`ring.func.base.BaseUserInterface.key` for the key.

        :see: The class documentation for common parameter details.
        :param Any value: The value to save in the storage.
        :rtype: None
        """
        raise NotImplementedError

    @abc.abstractmethod
    @interface_attrs(transform_args=transform_kwargs_only)
    def update(self, wire, **kwargs):  # pragma: no cover
        """Execute the original function and `set` the result as the value.

        This action is comprehensible as a concatenation of
        :meth:`ring.func.base.BaseUserInterface.execute` and
        :meth:`ring.func.base.BaseUserInterface.set`.

        :see: :meth:`ring.func.base.BaseUserInterface.key` for the key.
        :see: :meth:`ring.func.base.BaseUserInterface.execute` for the
            execution.

        :see: The class documentation for the parameter details.
        :return: The result of the original function.
        """
        raise NotImplementedError

    @abc.abstractmethod
    @interface_attrs(transform_args=transform_kwargs_only)
    def get_or_update(self, wire, **kwargs):  # pragma: no cover
        """Try to get and return the storage value; Otherwise, update and so.

        :see: :meth:`ring.func.base.BaseUserInterface.get` for get.
        :see: :meth:`ring.func.base.BaseUserInterface.update` for update.

        :see: The class documentation for the parameter details.
        :return: The storage value for the corresponding key if it exists;
            Otherwise result of the original function.
        """
        raise NotImplementedError

    @abc.abstractmethod
    @interface_attrs(transform_args=transform_kwargs_only)
    def delete(self, wire, **kwargs):  # pragma: no cover
        """Delete the storage value of the corresponding key.

        :see: :meth:`ring.func.base.BaseUserInterface.key` for the key.

        :see: The class documentation for the parameter details.
        :rtype: None
        """
        raise NotImplementedError

    @interface_attrs(transform_args=transform_kwargs_only)
    def has(self, wire, **kwargs):  # pragma: no cover
        """Return whether the storage has a value of the corresponding key.

        This is an optional function.

        :see: :meth:`ring.func.base.BaseUserInterface.key` for the key.

        :see: The class documentation for the parameter details.
        :return: Whether the storage has a value of the corresponding key.
        :rtype: bool
        """
        raise NotImplementedError

    @interface_attrs(transform_args=transform_kwargs_only)
    def touch(self, wire, **kwargs):  # pragma: no cover
        """Touch the storage value of the corresponding key.

        This is an optional function.

        :note: `Touch` means resetting the expiration.
        :see: :meth:`ring.func.base.BaseUserInterface.key` for the key.

        :see: The class documentation for the parameter details.
        :rtype: bool
        """
        raise NotImplementedError


def create_bulk_key(interface, wire, args):
    if isinstance(args, tuple):
        kwargs = wire._merge_args(args, {})
        return interface.key(wire, **kwargs)
    elif isinstance(args, dict):
        return interface.key(wire, **args)
    else:
        raise TypeError(
            "Each parameter of '_many' suffixed sub-functions must be an "
            "instance of 'tuple' or 'dict'")


def execute_bulk_item(wire, args):
    if isinstance(args, tuple):
        return wire.__func__(*args)
    elif isinstance(args, dict):
        return wire.__func__(**args)
    else:
        raise TypeError(
            "Each parameter of '_many' suffixed sub-functions must be an "
            "instance of 'tuple' or 'dict'")


class AbstractBulkUserInterfaceMixin(object):
    """Bulk access interface mixin.

    Every method in this mixin is optional. The methods have each
    corresponding function in :class:`ring.func.base.BaseUserInterface`.

    The parameters below describe common methods' parameters.

    :param ring.func.base.RingWire wire: The corresponding ring
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
        be always :class:`dict`. When there is a variable-length positional
        argument, pass the values them as a :class:`tuple` of parameters
        with the corresponding variable-length positional parameter name.
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

        :note: The semantics of this function may vary by the implementation.
        :see: The class documentation for the parameter details.
        :return: A sequence of the storage values or the executed result of the
            original function for the corresponding keys. When a key exists
            in the storage, the matching value is selected; Otherwise, the
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


@attr.s
class Config(object):
    coder = attr.ib()
    user_interface = attr.ib()
    storage_backend = attr.ib()
    storage_class = attr.ib()
    miss_value = attr.ib()
    default_action = attr.ib()
    key_encoding = attr.ib()
    expire_default = attr.ib()
    key_refactor = attr.ib()
    key_prefix = attr.ib()
    ignorable_keys = attr.ib()
    # wire_class = attr.ib()


class RingWire(Wire):

    __slots__ = ()

    def __init__(self, rope, *args, **kwargs):
        super(RingWire, self).__init__(rope, *args, **kwargs)

    @property
    def storage(self):
        return self._rope.storage

    def encode(self, v):
        return self._rope.encode(v)

    def decode(self, v):
        return self._rope.decode(v)

    def _merge_args(self, args, kwargs):
        """Create a fake kwargs object by merging actual arguments.

        The merging follows the signature of wrapped function and current
        instance.
        """
        # TODO: self._bound_objects must be empty for non-binding functions
        if type(self.__func__) is types.FunctionType:  # noqa
            bound_args = ()
        else:
            bound_args = range(len(self._bound_objects))
        full_kwargs = self._callable.kwargify(
            args, kwargs, bound_args=bound_args)
        return full_kwargs

    def run(self, action, *args, **kwargs):
        attr = getattr(self, action)
        return attr(*args, **kwargs)

    def _on_property(self):
        return self.run(self._rope.config.default_action)

    def __getattr__(self, name):
        try:
            return super(RingWire, self).__getattr__(name)
        except AttributeError:
            pass
        try:
            return self.__getattribute__(name)
        except AttributeError:
            pass

        attr = getattr(self._rope.config.user_interface, name)
        if callable(attr):
            transform_args = getattr(
                attr, 'transform_args', None)

            def impl_f(*args, **kwargs):
                if transform_args:
                    transform_func, transform_rules = transform_args
                    args, kwargs = transform_func(
                        self, transform_rules, args, kwargs)
                return attr(self, *args, **kwargs)

            cc = self._callable.wrapped_callable
            functools.wraps(cc)(impl_f)
            impl_f.__name__ = '.'.join((cc.__name__, name))
            if six.PY34:
                impl_f.__qualname__ = '.'.join((cc.__qualname__, name))

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


class PublicRing(object):

    def __init__(self, rope):
        self._rope = rope

    def key(self, func):
        self._rope.compose_key = func

    def encode(self, func):
        self._rope._encode = func

    def decode(self, func):
        self._rope._decode = func


class RingRope(RopeCore):
    def __init__(self, *args, **kwargs):
        super(RingRope, self).__init__(*args, **kwargs)

        self._encode = None
        self._decode = None

        self.ring = PublicRing(self)

    def compose_key(self, *bound_args, **kwargs):
        config = self.config

        _ignorable_keys = suggest_ignorable_keys(
            self.callable, self.config.ignorable_keys)
        _key_prefix = suggest_key_prefix(self.callable, config.key_prefix)

        c = self.callable
        key_generator = CallableKey(
            c, format_prefix=_key_prefix, ignorable_keys=_ignorable_keys)

        full_kwargs = kwargs.copy()
        for i, prearg in enumerate(bound_args):
            full_kwargs[c.parameters[i].name] = bound_args[i]

        in_memory_storage = hasattr(config.storage_class, 'in_memory_storage')
        coerced_kwargs = {
            k: coerce(v, in_memory_storage) for k, v in full_kwargs.items()
            if k not in _ignorable_keys}
        key = key_generator.build(coerced_kwargs)
        if config.key_encoding:
            key = key.encode(config.key_encoding)
        if config.key_refactor:
            key = config.key_refactor(key)
        return key

    @property
    def config(self):
        return self.rope._ring_object.config

    @property
    def encode(self):
        return self._encode or self.config.coder.encode

    @encode.setter
    def set_encode(self, value):
        self._encode = value

    @property
    def decode(self):
        return self._decode or self.config.coder.decode

    @decode.setter
    def set_decode(self, value):
        self._decode = value

    @cached_property
    def storage(self):
        # FIXME:
        return self.config.storage_class(self.ring, self.config.storage_backend)


class Ring(object):

    def __init__(self, allows_default_action=True, wire_slots=Ellipsis):
        self._config = None
        self._allows_default_action = allows_default_action

        # if wire_slots is Ellipsis:
        #     wire_slots = ()

        # func = self.__func__ if type(self.__func__) is types.FunctionType else Callable(self.__func__).wrapped_callable  # noqa
        # interface_keys = tuple(k for k in dir(user_interface) if k[0] != '_')

        class _RingWire(RingWire):
            # if wire_slots is not False:
            #     assert isinstance(wire_slots, tuple)
            #     __slots__ = interface_keys + wire_slots

            if allows_default_action:
                # @functools.wraps(func)
                def __call__(self, *args, **kwargs):
                    return self.run(self._rope.config.default_action, *args, **kwargs)

        self.wire_rope = WireRope(_RingWire, RingRope)
        self.wire_rope._ring_object = self

    @property
    def config(self):
        return self._config

    def configure(self,
                  storage_backend,  # actual storage
                  key_prefix,  # manual key prefix
                  expire_default,  # default expiration
                  # keyword-only arguments from here
                  # building blocks
                  coder, miss_value, user_interface, storage_class,
                  default_action=Ellipsis,
                  coder_registry=Ellipsis,
                  # key builder related parameters
                  ignorable_keys=None, key_encoding=None, key_refactor=None):
        """Configure ring object.

         This is the base factory function that every internal **Ring** factories
         are based on. See the source code of :mod:`ring.func.sync` or
         :mod:`ring.func.asyncio` for actual usages and sample code.

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
         :param Optional[ring.coder.Registry] coder_registry: The coder registry
             to load the given `coder`. The default value is
             :data:`ring.coder.registry` when :data:`None` is given.

         :param Optional[Callable[[type(Wire),type(Ring)],None]] on_manufactured:
             The callback function when a new ring wire or wire bridge is created.

         :param List[str] ignorable_keys: (experimental) Parameter names not to
             use to create storage key.
         :param Optional[str] key_encoding: The storage key is usually
             :class:`str` typed. When this parameter is given, a key is encoded
             into :class:`bytes` using the given encoding.
         :param Optional[Callable[[str],str]] key_refactor: Roughly,
             ``key = key_refactor(key)`` will be run when `key_refactor` is not
             :data:`None`; Otherwise it is omitted.

         :return: The factory decorator to create new ring wire or wire bridge.
         :rtype: (Callable)->ring.wire.RopeCore
         """

        if default_action is Ellipsis:
            default_action = 'get_or_update'
        assert bool(default_action) == bool(self._allows_default_action)
        if coder_registry is Ellipsis:
            coder_registry = default_registry
        raw_coder = coder
        ring_coder = coder_registry.get_or_coderize(raw_coder)

        if isinstance(user_interface, (tuple, list)):
            user_interface = type('_ComposedUserInterface', user_interface, {})

        self._config = Config(
            coder=ring_coder,
            user_interface=user_interface(self),
            storage_backend=storage_backend,
            storage_class=storage_class,
            miss_value=miss_value,
            default_action=default_action,
            key_encoding=key_encoding,
            expire_default=expire_default,
            key_refactor=key_refactor,
            key_prefix=key_prefix,
            ignorable_keys=ignorable_keys)

    def create_rope(self, func, callback=None):
        rope = self.wire_rope(func)

        if callback is not None:
            callback(wire_rope=rope)

        return rope


def factory(
        storage_backend,  # actual storage
        key_prefix,  # manual key prefix
        expire_default,  # default expiration
        # keyword-only arguments from here
        # building blocks
        coder, miss_value, user_interface, storage_class,
        default_action=Ellipsis,
        coder_registry=Ellipsis,
        # callback
        on_manufactured=None,
        # optimization
        wire_slots=Ellipsis,
        # key builder related parameters
        ignorable_keys=None, key_encoding=None, key_refactor=None):
    """Create a decorator which turns a function into ring wire or wire bridge.

    This is the base factory function that every internal **Ring** factories
    are based on. See the source code of :mod:`ring.func.sync` or
    :mod:`ring.func.asyncio` for actual usages and sample code.

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
    :param Optional[ring.coder.Registry] coder_registry: The coder registry
        to load the given `coder`. The default value is
        :data:`ring.coder.registry` when :data:`None` is given.

    :param Optional[Callable[[type(Wire),type(Ring)],None]] on_manufactured:
        The callback function when a new ring wire or wire bridge is created.

    :param List[str] ignorable_keys: (experimental) Parameter names not to
        use to create storage key.
    :param Optional[str] key_encoding: The storage key is usually
        :class:`str` typed. When this parameter is given, a key is encoded
        into :class:`bytes` using the given encoding.
    :param Optional[Callable[[str],str]] key_refactor: Roughly,
        ``key = key_refactor(key)`` will be run when `key_refactor` is not
        :data:`None`; Otherwise it is omitted.

    :return: The factory decorator to create new ring wire or wire bridge.
    :rtype: (Callable)->ring.wire.RopeCore
    """

    def _decorator(f):
        ring = Ring(allows_default_action=bool(default_action), wire_slots=wire_slots)
        ring.configure(
            storage_backend,
            key_prefix,
            expire_default,
            # keyword-only arguments from here
            # building blocks
            coder, miss_value, user_interface, storage_class,
            default_action,
            coder_registry,
            # key builder related parameters
            ignorable_keys, key_encoding, key_refactor)

        return ring.create_rope(f, on_manufactured)

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
    :class:`ring.func.base.CommonMixinStorage` and a subclass of
    :class:`ring.func.base.StorageMixin`.

    When subclassing this interface, remember `get` and `set` methods must
    include coder works. The methods marked as :func:`abc.abstractmethod`
    are mandatory; Otherwise not.
    """

    def __init__(self, ring, backend):
        self._ring = ring
        if contextvars:
            self._backend = (lambda: backend.get()) if isinstance(backend, contextvars.ContextVar) else (lambda: backend)
        else:
            self._backend = lambda: backend

    @property
    def backend(self):
        return self._backend()

    @property
    def rope(self):
        return self._ring._rope

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
    def has(self, key):  # pragma: no cover
        """Check data exists for given key."""
        raise NotImplementedError

    @abc.abstractmethod
    def touch(self, key, expire=Ellipsis):  # pragma: no cover
        """Touch data by given key."""
        raise NotImplementedError


class CommonMixinStorage(BaseStorage):
    """General storage root for StorageMixin."""

    def get(self, key):
        value = self.get_value(key)
        return self.rope.decode(value)

    def set(self, key, value, expire=Ellipsis):
        if expire is Ellipsis:
            expire = self.rope.config.expire_default
        encoded = self.rope.encode(value)
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
            expire = self.rope.config.expire_default
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


def asyncio_binary_classifier(f):
    c = Callable(f)
    return int(bool(c.is_coroutine))


def create_factory_proxy(proxy_base, classifier, factory_table):
    proxy_class = type(
        'ring.create_factory_proxy.<locals>._FactoryProxy', (proxy_base,), {})
    proxy_class.classifier = staticmethod(classifier)
    proxy_class.factory_table = staticmethod(factory_table)
    sample_factory = factory_table[0]
    proxy_class.__call__ = functools.wraps(sample_factory)(proxy_class.__call__)
    proxy_class.__doc__ = sample_factory.__doc__
    return proxy_class


class FactoryProxyMetaclass(type):

    def __repr__(cls):
        factory_table_body = ', '.join(
            '{i}: {factory.__module__}.{factory.__name__}'.format(
                i=i, factory=factory)
            for i, factory in enumerate(cls.factory_table))
        factory_table = '{' + factory_table_body + '}'
        f = '<{cls.__base__.__name__} subclass with (' \
            'factory_table={factory_table}, ' \
            'classifier={cls.classifier.__module__}.{classifier})>'
        return f.format(
            cls=cls,
            factory_table=factory_table, classifier=qualname(cls.classifier))


class FactoryProxyBase(six.with_metaclass(FactoryProxyMetaclass, object)):

    classifier = None  # must be set in descendant
    factory_table = None  # must be set in descendant

    def __init__(self, *args, **kwargs):
        self.pargs = args, kwargs
        self.rings = {}

    def __call__(self, func):
        key = self.classifier(func)
        if key not in self.rings:
            factory = self.factory_table[key]
            args, kwargs = self.pargs
            ring = factory(*args, **kwargs)
            self.rings[key] = factory
        else:
            ring = self.rings[key]
        return ring(func)

    def __repr__(self):
        return u'{cls.__name__}(*{args}, **{kwargs})'.format(
            cls=type(self),
            args=repr(self.pargs[0]), kwargs=repr(self.pargs[1]))
