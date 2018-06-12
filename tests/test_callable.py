
import sys
import pytest

from ring.callable import Callable


if sys.version_info[0] >= 3:
    from ._test_callable_py3 import *  # noqa


@pytest.mark.parametrize('f,args,kwargs,merged', [
    (lambda: None, (), {}, {}),
    (lambda x, y: None, (1, 2), {}, dict(x=1, y=2)),
    (lambda x, y, z=30: None, (1, 2), {}, dict(x=1, y=2, z=30)),
    (lambda x, y, z=30: None, (1,), {'y': 2}, dict(x=1, y=2, z=30)),
    (lambda x, y, z=30: None, (1, 2, 3), {}, dict(x=1, y=2, z=3)),
    (lambda x, y, z=30: None, (1,), {'y': 20}, dict(x=1, y=20, z=30)),
    (lambda x, y, *args: None, (1,), {'y': 20}, dict(x=1, y=20, args=())),
    (lambda x, y, *args: None, (1, 2, 3, 4, 5), {}, dict(x=1, y=2, args=(3, 4, 5))),
    (lambda x, **kw: None, (), {'x': 10, 'y': 20, 'z': 30}, dict(x=10, kw={'y': 20, 'z': 30})),
    (lambda x, *args, **kw: None, (1, 2, 3, 4), {'y': 20, 'z': 30}, dict(x=1, args=(2, 3, 4), kw={'y': 20, 'z': 30})),
])
def test_kwargify(f, args, kwargs, merged):
    kwargified = Callable(f).kwargify(args, kwargs)
    print(kwargified)
    print(merged)
    assert kwargified == merged


@pytest.mark.parametrize('f,args,kwargs,exc', [
    (lambda: None, (1, 2), {}, TypeError),
    (lambda x, y: None, (2, 3), {'x': 1}, TypeError),
    (lambda x, y, z=30: None, (1,), {}, TypeError),
    (lambda x, y, z=30: None, (1,), {'x': 2}, TypeError),
])
def test_kwargify_exc(f, args, kwargs, exc):
    with pytest.raises(exc):
        Callable(f).kwargify(args, kwargs)


def test_empty_annotations():
    c = Callable(lambda a, *b, **c: None)
    assert c.annotations == {}


def test_callable_attributes():

    def f():
        pass
    w = Callable(f)
    assert w.is_barefunction is True
    assert w.is_descriptor is False
    assert w.is_membermethod is False
    assert w.is_classmethod is False

    class A():

        def m(self):
            pass
        w = Callable(m)
        assert w.is_barefunction is False
        assert w.is_descriptor is False
        assert w.is_membermethod is True
        assert w.is_classmethod is False

        @classmethod
        def c(cls):
            pass
        w = Callable(c)
        assert w.is_barefunction is False
        assert w.is_descriptor is True
        assert w.is_membermethod is False
        assert w.is_classmethod is True

        @staticmethod
        def s():
            pass
        w = Callable(s)
        assert w.is_barefunction is False
        assert w.is_descriptor is True
        assert w.is_membermethod is False
        assert w.is_classmethod is False
