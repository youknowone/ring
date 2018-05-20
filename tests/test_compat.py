
from ring._compat import qualname


def test_qualname():

    class A(object):
        def f():
            pass

    assert qualname(A.f).endswith('A.f')
