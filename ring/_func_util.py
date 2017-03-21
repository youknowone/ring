import functools
from ring.key import CallableWrapper, CallableKey


def bypass(x):
    return x


def unpack_coder(coder):
    if coder:
        if isinstance(coder, str):
            import ring.coder
            loaded_coder = getattr(ring.coder, coder, None)
            if loaded_coder is None:
                raise TypeError(
                    "Argument 'coder' is an instance of 'str' but built-in "
                    "coder '{}' does not exist".format(coder))
            coder = loaded_coder

        if isinstance(coder, tuple):
            encode, decode = coder
        else:
            encode, decode = coder.encode, coder.decode
    else:
        encode, decode = bypass, bypass

    return encode, decode


def is_method(f):
    fw = CallableWrapper(f)
    return fw.first_varname == 'self'


def is_classmethod(f):
    fw = CallableWrapper(f)
    return fw.first_varname == 'cls'


def suggest_ignorable_keys(f, ignorable_keys):
    if ignorable_keys is None:
        if is_classmethod(f):
            _ignorable_keys = ['cls']
        else:
            _ignorable_keys = []
    else:
        _ignorable_keys = ignorable_keys
    return _ignorable_keys


def suggest_key_prefix(f, key_prefix):
    if key_prefix is None:
        if is_method(f):
            key_prefix = \
                '{0.__module__}.{{self.__class__.__name__}}.' \
                '{0.__name__}'.format(f)
        elif is_classmethod(f):
            # No guess supported for classmethod yet.
            key_prefix = '{0.__module__}.{0.__name__}'.format(f)
        else:
            key_prefix = '{0.__module__}.{0.__name__}'.format(f)
    return key_prefix


def coerce(v):
    if isinstance(v, (int, str, bool)):
        return v

    if isinstance(v, list):
        return str(v).replace(' ', '')

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


def create_ckey(f, key_prefix, ignorable_keys, coerce=coerce, encoding=None):
    ckey = CallableKey(
        f, format_prefix=key_prefix, ignorable_keys=ignorable_keys)

    def build_key(args, kwargs):
        full_kwargs = ckey.merge_kwargs(args, kwargs)
        coerced_kwargs = {k: coerce(v) for k, v in full_kwargs.items()}
        key = ckey.build(coerced_kwargs)
        if encoding:
            key = key.encode(encoding)
        return key

    ckey.build_key = build_key

    return ckey


class WrapperBase(object):

    def __init__(self, preargs, anon_padding=False):
        assert isinstance(preargs, tuple)
        self.preargs = preargs
        self.anon_padding = anon_padding

    def reargs(self, args, padding):
        if self.preargs:
            args = self.preargs + args
        elif padding and self.anon_padding:
            args = (None,) + args
        return args


def factory(
        context, key_prefix, wrapper_class,
        get_value, set_value, del_value, touch_value, miss_value, coder,
        ignorable_keys=None, key_encoding=None):

    encode, decode = unpack_coder(coder)

    def _decorator(f):
        _ignorable_keys = suggest_ignorable_keys(f, ignorable_keys)
        _key_prefix = suggest_key_prefix(f, key_prefix)
        ckey = create_ckey(
            f, _key_prefix, _ignorable_keys, encoding=key_encoding)

        _Wrapper = wrapper_class(
            f, context, ckey,
            get_value, set_value, del_value, touch_value, miss_value,
            encode, decode)

        if is_method(f):
            @property
            def _w(self):
                wrapper_name = '__wrapper_' + f.__name__
                wrapper = getattr(self, wrapper_name, None)
                if wrapper is None:
                    _wrapper = _Wrapper((self,))
                    wrapper = functools.wraps(f)(_wrapper)
                    setattr(self, wrapper_name, wrapper)
                return wrapper
        elif is_classmethod(f):
            _w = _Wrapper((), anon_padding=True)
        else:
            _w = _Wrapper(())

        return _w

    return _decorator
