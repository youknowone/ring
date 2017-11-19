import functools


class WiredProperty(object):

    def __init__(self, func):
        self.__func__ = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self.__func__(type)
        else:
            return self.__func__(obj)


class Wire(object):

    @classmethod
    def for_callable(cls):
        from ring.func_base import is_method, is_classmethod
        _callable = cls._callable

        _shared_attrs = {}
        _dynamic_attrs = {}

        if is_method(_callable) or is_classmethod(_callable):
            @WiredProperty
            def _w(self):
                wrapper_name = '__wrapper_' + _callable.code.co_name
                wrapper = getattr(self, wrapper_name, None)
                if wrapper is None:
                    _wrapper = cls((self,))
                    wrapper = functools.wraps(_callable.callable)(_wrapper)
                    setattr(self, wrapper_name, wrapper)
                    _wrapper._shared_attrs = _shared_attrs
                    _wrapper._dynamic_attrs = _dynamic_attrs
                return wrapper
        else:
            _w = cls(())

        _w._shared_attrs = _shared_attrs
        _w._dynamic_attrs = _dynamic_attrs

        return _w

    def __init__(self, preargs):
        assert isinstance(preargs, tuple)
        self.preargs = preargs

    def reargs(self, args):
        if self.preargs:
            args = self.preargs + args
        return args

    def merge_args(self, args, kwargs):
        args = self.reargs(args)
        full_kwargs = self._callable.kwargify(args, kwargs)
        if self.preargs:
            full_kwargs.pop(self._callable.arguments[0].varname)
        return full_kwargs

    def __getattr__(self, name):
        try:
            return self.__getattribute__(name)
        except AttributeError:
            pass

        attr = self._dynamic_attrs.get(name)
        if callable(attr):
            def impl_f(*args, **kwargs):
                args = self.reargs(args)
                return attr(*args, **kwargs)
            setattr(self, name, impl_f)

        return self.__getattribute__(name)
