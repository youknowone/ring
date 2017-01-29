
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
                    "Argument 'coder' is an instance of 'str' but built-in coder "
                    "'{}' does not exist".format(coder))
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
            key_prefix = '{0.__module__}.{{self.__class__.__name__}}.{0.__name__}'.format(f)
        elif is_classmethod(f):
            # No guess supported for classmethod yet.
            key_prefix = '{0.__module__}.{0.__name__}'.format(f)
        else:
            key_prefix = '{0.__module__}.{0.__name__}'.format(f)
    return key_prefix


def coerce_value(v):
    if isinstance(v, (int, str, bool)):
        return v

    if hasattr(v, '__ring_key__'):
        return v.__ring_key__()

    cls = v.__class__
    if cls.__str__ != object.__str__:
        return str(v)

    raise TypeError(
        "The given value '{}' of type '{}' is not key-compatible type. "
        "Add __ring_key__() or __str__().".format(v, cls))


def create_ckey(f, key_prefix, ignorable_keys, coerce=coerce_value, encoding=None):
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
