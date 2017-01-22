
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
    return fw.code.co_varnames and fw.code.co_varnames[0] in ('self', 'cls')


def create_ckey(f, key_prefix, args_prefix_size, ignorable_keys, encoding=None):
    fw = CallableWrapper(f)
    ckey = CallableKey(
        fw, format_prefix=key_prefix,
        args_prefix_size=args_prefix_size,
        ignorable_keys=ignorable_keys or [])

    def build_key(args, kwargs):
        full_kwargs = ckey.merge_kwargs(args, kwargs)
        key = ckey.build(full_kwargs)
        if encoding:
            key = key.encode(encoding)
        return key

    ckey.build_key = build_key

    return ckey


class WrapperBase(object):

    def __init__(self, preargs):
        assert isinstance(preargs, tuple)
        self.preargs = preargs

    def reargs(self, args):
        if self.preargs:
            args = self.preargs + args
        return args
