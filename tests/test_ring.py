
import ring


class A():

    def __init__(self, v):
        self.v = v

    def __ring_key__(self):
        return str(self.v)

    @ring.dict({})
    def x(self):
        return self.v


def test_ring_wrapper():

    a = A(10)
    b = A(20)
    assert a.x() == 10
    assert b.x() == 20
    assert a.x() == 10
    assert b.x() == 20
