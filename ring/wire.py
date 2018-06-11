""":mod:`ring.wire` --- Universal method/function wrapper.
==========================================================
"""
from .callable import Callable
from ._compat import functools
from ._util import cached_property


@functools.singledispatch
def descriptor_bind(descriptor, obj, type):
    return obj


@descriptor_bind.register(staticmethod)
@descriptor_bind.register(classmethod)
def descriptor_bind_(descriptor, obj, type):
    return type


class Wire(object):
    """The core data object for each function for bound method.

    Inherit this class to implement your own Wire classes.

    - For normal functions, each function is directly wrapped by **Wire**.
    - For any methods or descriptors (including classmethod, staticmethod),
      each one is wrapped by :class:`ring.wire.MethodRopeMixin`
      and it creates **Wire** object for each bound object.
    """

    def __init__(self, rope, binding):
        self._rope = rope
        self._callable = rope.callable
        self._binding = binding
        if binding:
            self.__func__ = self._callable.wrapped_object.__get__(*binding)
        else:
            self.__func__ = self._callable.wrapped_object

    @cached_property
    def _bound_objects(self):
        if self._binding is None:
            return ()
        else:
            return (descriptor_bind(
                self._callable.wrapped_object, *self._binding),)


class RopeCore(object):

    def __init__(self, callable, rope):
        super(RopeCore, self).__init__()
        self.callable = callable
        self.rope = rope
        self.wire_class = rope.wire_class


class MethodRopeMixin(object):

    def __init__(self, *args, **kwargs):
        super(MethodRopeMixin, self).__init__(*args, **kwargs)
        assert not self.callable.is_barefunction

    def __get__(self, obj, type=None):
        cw = self.callable
        co = cw.wrapped_object
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
            wire = self.wire_class(self, (obj, type))
            wrapper = functools.wraps(boundmethod)(wire)
            setattr(owner, wrapper_name, wrapper)
        return wrapper


class FunctionRopeMixin(object):

    def __init__(self, *args, **kwargs):
        super(FunctionRopeMixin, self).__init__(*args, **kwargs)
        assert self.callable.is_barefunction
        boundmethod = self.callable.wrapped_object
        wire = self.wire_class(self, None)
        self._wire = functools.wraps(boundmethod)(wire)

    def __getattr__(self, name):
        try:
            return self.__getattribute__(name)
        except AttributeError:
            pass
        return getattr(self._wire, name)


class CallableRopeMixin(object):

    def __init__(self, *args, **kwargs):
        super(CallableRopeMixin, self).__init__(*args, **kwargs)
        self.__call__ = functools.wraps(self.callable.wrapped_object)(self)

    def __call__(self, *args, **kwargs):
        return self._wire(*args, **kwargs)


class WireRope(object):

    def __init__(self, wire_class, core_class=RopeCore):
        if isinstance(core_class, tuple):
            core_classes = core_class
        else:
            core_classes = (core_class,)

        self.wire_class = wire_class
        self.method_rope = type(
            '_MethodRope', (MethodRopeMixin,) + core_classes, {})
        self.function_rope = type(
            '_FunctionRope', (FunctionRopeMixin,) + core_classes, {})
        self.callable_function_rope = type(
            '_CallableFunctionRope',
            (CallableRopeMixin, FunctionRopeMixin,) + core_classes, {})

    def __call__(self, function):
        """Wrap a function/method definition.

        :return: Wrapper object. The return type is up to given callable is
                 function or method.
        """
        wrapper = Callable(function)
        if wrapper.is_barefunction:
            if hasattr(self.wire_class, '__call__'):
                rope_class = self.callable_function_rope
            else:
                rope_class = self.function_rope
        else:
            rope_class = self.method_rope
        rope = rope_class(wrapper, rope=self)
        return rope
