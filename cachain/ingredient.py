

class Key(object):

    def __init__(self, key):
        self.key = key

    def build(self, args):
        raise NotImplementedError


class FormatKey(Key):

    def build(self, args):
        return self.key.format(**args)


class CallableKey(Key):

    def build(self, args):
        return self.key(**args)


class Ring(object):

    def __init__(self, storage, key):
        self.storage = storage
        if not isinstance(key, Key):
            if isinstance(key, (str, unicode)):
                key = FormatKey(key)
            elif callable(key):
                key = CallableKey(key)
            else:
                raise TypeError
        self.key = key

    @staticmethod
    def _key_args(args, kwargs):
        if args and kwargs:
            raise TypeError
        if args and len(args) > 1:
            raise TypeError
        if args:
            key = args[0]
        else:
            key = kwargs
        return key

    def get(self, *args, **kwargs):
        key_args = self._key_args(args, kwargs)
        return self.get_by_key(key_args)

    def get_by_key(self, key_args):
        built_key = self.key.build(key_args)
        return self.storage.get(built_key)

    def set(self, _value, *args, **kwargs):
        key_args = self._key_args(args, kwargs)
        if callable(_value):
            _value = _value(**key_args)
        return self.set_by_key(_value, key_args)

    def set_by_key(self, value, key_args):
        built_key = self.key.build(key_args)
        return self.storage.set(built_key, value)

    def get_or_set(self, _value, *args, **kwargs):
        key_args = self._key_args(args, kwargs)
        value = self.get_by_key(key_args)
        if value is None:
            value = _value(**key_args)
            self.set_by_key(value, key_args)
        return value
