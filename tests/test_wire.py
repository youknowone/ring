
from ring.wire import Wire
from ring.key import CallableWrapper


def test_wire():

    class TestWire(Wire):
        pass

    def wrapper(f):
        c = CallableWrapper(f)
        w = TestWire.for_callable(c)
        return w

    class A(object):

        @wrapper
        def f(self):
            return 10

        @f._add_function('call')
        def f_call(self):
            return self.f._callable.callable(self)

        @f._add_function('key')
        def f_key(self):
            return 'key'

    a = A()

    assert a.f.call() == 10
    assert a.f.key() == 'key'
