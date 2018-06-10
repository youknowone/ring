
from ring.wire import Wire
from ring.key import Callable


def test_wire():

    class TestWire(Wire):
        pass

    def wrapper(f):
        c = Callable(f)
        w = TestWire.for_callable(c)
        return w

    class A(object):

        def __init__(self, v):
            self.v = v

        @wrapper
        def f(self):
            return self.v

        @f._add_function('call')
        def f_call(self, wire):
            return wire.__func__()

        @f._add_function('key')
        def f_key(self, wire):
            return 'key'

    a = A(10)
    assert a.f.call() == 10
    assert a.f.key() == 'key'

    b = A(20)
    assert a.f.call() == 10, (a.f, a.f.call())
    assert b.f.call() == 20, (b.f, b.f.call())

    assert isinstance(A.f, TestWire)
    assert isinstance(a.f, TestWire)
    assert A.f is not a.f
