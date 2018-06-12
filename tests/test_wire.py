
from ring.wire import Wire, WireRope


def test_wire():

    class TestWire(Wire):
        x = 7

        def y(self):
            return self._bound_objects[0].v

    class CallableWire(Wire):
        def __call__(self):
            return self._bound_objects[0].v

    test_rope = WireRope(TestWire)
    callable_rope = WireRope(CallableWire)

    class A(object):

        def __init__(self, v):
            self.v = v

        @test_rope
        def f(self):
            return self.v

        @callable_rope
        def g(self):
            return self.v

    a = A(10)
    b = A(20)

    assert a.f.x == 7
    assert a.f.y() == 10
    assert b.f.y() == 20
    assert not callable(a.f)
    assert a.g() == 10
    assert b.g() == 20
    assert callable(a.g)
