import functools
from ring.key import CallableWrapper, CallableKey
from ring.wire import Wire
from ring.coder import registry as coder_registry


def is_method(c):
    if not c.first_argument:
        return False
    return c.first_argument.varname == 'self'


def is_classmethod(c):
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


def coerce(v):
    if isinstance(v, (int, str, bool)):
        return v

    if isinstance(v, (list, tuple)):
        return str(v).replace(' ', '')

    if isinstance(v, type):
        return v.__name__

    if hasattr(v, '__ring_key__'):
        return v.__ring_key__()

    if isinstance(v, dict):
        return ','.join(['{},{}'.format(k, v[k]) for k in sorted(v.keys())])

    if isinstance(v, (set, frozenset)):
        return ','.join(sorted(v))

    # NOTE: general sequence processing is good -
    # but NEVER add a general iterator processing. it will cause user bug.

    cls = v.__class__
    if cls.__str__ != object.__str__:
        return str(v)

    raise TypeError(
        "The given value '{}' of type '{}' is not a key-compatible type. "
        "Add __ring_key__() or __str__().".format(v, cls))


class RingBase(Wire):
    # for now, RingBase is not well seperated from Wire

    def merge_args(self, args, kwargs):
        args = self._reargs(args)
        full_kwargs = self._callable.kwargify(args, kwargs)
        if self._preargs:
            full_kwargs.pop(self._callable.arguments[0].varname)
        return full_kwargs

    def __getattr__(self, name):
        try:
            return super(RingBase, self).__getattr__(name)
        except AttributeError:
            pass
        try:
            return self.__getattribute__(name)
        except AttributeError:
            pass

        interface_name = '_' + name
        if hasattr(self._interface_class, interface_name):
            attr = self.__getattribute__(interface_name)
            if callable(attr):
                @functools.wraps(self._callable.callable)
                def impl_f(*args, **kwargs):
                    full_kwargs = self.merge_args(args, kwargs)
                    return attr(**full_kwargs)
                setattr(self, name, impl_f)

        return self.__getattribute__(name)


def create_ckey(c, key_prefix, ignorable_keys, coerce=coerce, encoding=None, key_refactor=lambda x: x):
    assert isinstance(c, CallableWrapper)
    ckey = CallableKey(
        c, format_prefix=key_prefix, ignorable_keys=ignorable_keys)

    def build_key(preargs, kwargs):
        full_kwargs = kwargs.copy()
        for i, prearg in enumerate(preargs):
            full_kwargs[c.positional_arguments[i].varname] = preargs[i]
        coerced_kwargs = {k: coerce(v) for k, v in full_kwargs.items()}
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

    encode, decode = coder_registry.get(coder)

    def _decorator(f):
        _callable = CallableWrapper(f)
        _ignorable_keys = suggest_ignorable_keys(_callable, ignorable_keys)
        _key_prefix = suggest_key_prefix(_callable, key_prefix)
        ckey = create_ckey(
            _callable, _key_prefix, _ignorable_keys, encoding=key_encoding, key_refactor=key_refactor)

        return ring_factory(
            _callable, context, ckey, RingBase,
            interface, storage_implementation, miss_value, expire_default,
            encode, decode).for_callable(_callable)

    return _decorator


class NotFound(Exception):
    pass


class StorageImplementation(object):

    def get_value(self, obj, key):  # pragma: no cover
        raise NotImplementedError

    def set_value(self, obj, key, value, expire):  # pragma: no cover
        raise NotImplementedError

    def del_value(self, obj, key):  # pragma: no cover
        raise NotImplementedError

    def touch_value(self, obj, key, expire):
        raise NotImplementedError


class BaseInterface(object):

    def _key(self, **kwargs):
        args = self._preargs
        return self._ckey.build_key(args, kwargs)

    def _execute(self, **kwargs):
        return self._p_execute(kwargs)

    def _get(self, **kwargs):  # pragma: no cover
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
