import functools


class WiredProperty(object):

    def __init__(self, func):
        self.__func__ = func

    def __get__(self, obj, type=None):
        if obj is None:
            return self.__func__(type)
        else:
            return self.__func__(obj)

    def _add_function(self, key):
        def _w(f):
            setattr(self, key, f)
            self._dynamic_attrs[key] = f
            return f
        return _w


class Wire(object):

    @classmethod
    def for_callable(cls, cwrapper):
        from ring.func_base import is_method, is_classmethod

        _shared_attrs = {'attrs': {}}

        if is_method(cwrapper) or is_classmethod(cwrapper):
            @WiredProperty
            def _w(self):
                wrapper_name = '__wrapper_' + cwrapper.code.co_name
                wrapper = getattr(self, wrapper_name, None)
                if wrapper is None:
                    _wrapper = cls(cwrapper, _shared_attrs)
                    _wrapper._preargs = (self,)
                    wrapper = functools.wraps(cwrapper.callable)(_wrapper)
                    setattr(self, wrapper_name, wrapper)
                    _wrapper._shared_attrs = _shared_attrs
                return wrapper

            _w._dynamic_attrs = _shared_attrs['attrs']
        else:
            _w = cls(cwrapper, _shared_attrs)
            _w._preargs = ()

        _w.cwrapper = cwrapper
        _w._shared_attrs = _shared_attrs

        return _w

    def __init__(self, cwrapper, shared_attrs):
        self.cwrapper = cwrapper
        self._shared_attrs = shared_attrs

    @property
    def _dynamic_attrs(self):
        return self._shared_attrs.get('attrs', ())

    def _reargs(self, args):
        if self._preargs:
            args = self._preargs + args
        return args

    def merge_args(self, args, kwargs):
        args = self._reargs(args)
        full_kwargs = self.cwrapper.kwargify(args, kwargs)
        if self._preargs:
            full_kwargs.pop(self.cwrapper.first_parameter.name)
        return full_kwargs

    def __getattr__(self, name):
        try:
            return self.__getattribute__(name)
        except AttributeError:
            pass

        attr = self._dynamic_attrs.get(name)
        if callable(attr):
            def impl_f(*args, **kwargs):
                args = self._reargs(args)
                return attr(*args, **kwargs)
            setattr(self, name, impl_f)

        return self.__getattribute__(name)
