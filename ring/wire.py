""":mod:`ring.wire` --- Universal method/function wrapper.
==========================================================
"""
import functools


class WiredProperty(object):
    """Wire-friendly property to create method wrapper for each instance.

    When the property is wrapping a method or a class method,
    :class:`ring.wire.Wire` object will be created for each distinguishable
    owner instance and class.
    """

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
    """The universal method/function wrapper.

    - For normal functions, each function is directly wrapped by **Wire**.
    - For methods, each method is wrapped by :class:`ring.wire.WiredProperty`
      and it creates **Wire** object for each instance.
    - For class methods, each class method is wrapped by
      :class:`ring.wire.WiredProperty` and it creates **Wire** object for
      each subclass.

    :note: DO NOT manually instantiate a **Wire** object. That's not what
           you want to do.
    :see: :meth:`ring.wire.Wire.for_callable` for actual wrapper function.
    """

    @classmethod
    def for_callable(cls, cwrapper):
        """Wrap a function/method definition.

        :return: Wrapper object. The return type is up to given callable is
                 function or method.
        :rtype: ring.wire.Wire or ring.wire.WiredProperty
        """
        from ring.func_base import is_method, is_classmethod

        _shared_attrs = {'attrs': {}}

        c_is_method = is_method(cwrapper)
        c_is_classmethod = is_classmethod(cwrapper)
        if c_is_method or c_is_classmethod:
            @WiredProperty
            def _w(self):
                wrapper_name_parts = ['__wire_', cwrapper.code.co_name]
                if c_is_classmethod:
                    self_cls = self if type(self) == type else type(self)  # fragile
                    wrapper_name_parts.extend(('_', self_cls.__name__))
                    self = self_cls
                wrapper_name = ''.join(wrapper_name_parts)
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

        functools.wraps(cwrapper.callable)(_w)
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
        """Create a fake kwargs object by merging actual arguments.

        The merging follows the signature of wrapped function and current
        instance.
        """
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
