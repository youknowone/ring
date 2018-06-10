""":mod:`ring.wire` --- Universal method/function wrapper.
==========================================================
"""
from ._compat import functools
from ._util import cached_property


@functools.singledispatch
def descriptor_bind(descriptor, obj, type):
    return obj


@descriptor_bind.register(staticmethod)
@descriptor_bind.register(classmethod)
def descriptor_bind_(descriptor, obj, type):
    return type


class WiredProperty(object):
    """Wire-friendly property to create method wrapper for each instance.

    When the property is wrapping a method or a class method,
    :class:`ring.wire.Wire` object will be created for each distinguishable
    owner instance and class.
    """

    def __init__(self, func):
        self.__func__ = func

    def __get__(self, obj, type=None):
        return self.__func__(obj, type)

    def _add_function(self, key):
        def _decorator(f):
            self._dynamic_attrs[key] = f
            return f
        return _decorator


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
    def for_callable(cls, cw):
        """Wrap a function/method definition.

        :return: Wrapper object. The return type is up to given callable is
                 function or method.
        :rtype: ring.wire.Wire or ring.wire.WiredProperty
        """
        _shared_attrs = {'attrs': {}}

        if not cw.is_barefunction:
            co = cw.wrapped_object

            def __w(obj, type):
                owner = descriptor_bind(co, obj, type)
                if owner is None:  # invalid binding but still wire it
                    owner = obj if obj is not None else type
                wrapper_name_parts = ['__wire_', cw.wrapped_callable.__name__]
                if owner is type:
                    wrapper_name_parts.extend(('_', type.__name__))
                wrapper_name = ''.join(wrapper_name_parts)
                wrapper = getattr(owner, wrapper_name, None)
                if wrapper is None:
                    boundmethod = co.__get__(obj, type)
                    wire = cls(cw, (obj, type), _shared_attrs)
                    wrapper = functools.wraps(boundmethod)(wire)
                    setattr(owner, wrapper_name, wrapper)
                    wire._shared_attrs = _shared_attrs
                return wrapper

            _w = WiredProperty(__w)
            _w._dynamic_attrs = _shared_attrs['attrs']
        else:
            _w = cls(cw, None, _shared_attrs)

        _w._callable = cw
        _w._shared_attrs = _shared_attrs

        functools.wraps(cw.wrapped_callable)(_w)
        return _w

    @cached_property
    def _bound_objects(self):
        if self._binding is None:
            return ()
        else:
            return (descriptor_bind(
                self._callable.wrapped_object, *self._binding), )

    def __init__(self, callable, binding, shared_attrs):
        self._callable = callable
        self._binding = binding
        if binding:
            self.__func__ = callable.wrapped_object.__get__(*binding)
        else:
            self.__func__ = callable.wrapped_object
        self._shared_attrs = shared_attrs

    @property
    def _dynamic_attrs(self):
        return self._shared_attrs.get('attrs', ())

    def __getattr__(self, name):
        try:
            return self.__getattribute__(name)
        except AttributeError:
            pass

        if name in self._dynamic_attrs:
            attr = self._dynamic_attrs.get(name)
            if self._binding:
                attr = attr.__get__(*self._binding)

            def impl_f(*args, **kwargs):
                return attr(self, *args, **kwargs)

            setattr(self, name, impl_f)

        return self.__getattribute__(name)
