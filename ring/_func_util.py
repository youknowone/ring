
from ring.key import CallableKey


def _bypass(x):
    return x


def _unpack_coder(coder):
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
        encode, decode = _bypass, _bypass

    return encode, decode


def _create_ckey(f, key_prefix, args_prefix_size, ignorable_keys, encoding=None):
    ckey = CallableKey(
        f, format_prefix=key_prefix,
        args_prefix_size=args_prefix_size or 0,
        ignorable_keys=ignorable_keys or [])
    if args_prefix_size is None:
        if f.__code__.co_varnames and f.__code__.co_varnames[0] in ('self', 'cls'):
            ckey.args_prefix_size = 1

    def build_key(args, kwargs):
        full_kwargs = ckey.merge_kwargs(args, kwargs)
        key = ckey.build(full_kwargs)
        if encoding:
            key = key.encode(encoding)
        return key

    ckey.build_key = build_key

    return ckey
