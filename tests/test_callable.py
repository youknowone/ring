import sys
import pytest

from ring.callable import Callable
from ring.func.base import ArgPack


if sys.version_info >= (3, 8):
    from ._test_callable_py3 import *  # noqa

    test_make_labels_py3 = eval(
        r"""[
            (lambda x, /, y: None, ArgPack((), (1, 2), {}), {"x": 1, "y": 2}),
        ]"""
    )
else:
    test_make_labels_py3 = []


@pytest.mark.parametrize(
    "f,pargs,merged",
    [
        (lambda: None, ArgPack((), (), {}), {}),
        (lambda x, y: None, ArgPack((), (1, 2), {}), {"x": 1, "y": 2}),
        (lambda x, y, z=30: None, ArgPack((), (1, 2), {}), {"x": 1, "y": 2, "z": 30}),
        (
            lambda x, y, z=30: None,
            ArgPack((), (1,), {"y": 2}),
            {"x": 1, "y": 2, "z": 30},
        ),
        (lambda x, y, z=30: None, ArgPack((), (1, 2, 3), {}), {"x": 1, "y": 2, "z": 3}),
        (
            lambda x, y, z=30: None,
            ArgPack((), (1,), {"y": 20}),
            {"x": 1, "y": 20, "z": 30},
        ),
        (
            lambda x, y, *args: None,
            ArgPack((), (1,), {"y": 20}),
            {"x": 1, "y": 20, "*args": ()},
        ),
        (
            lambda x, y, *args: None,
            ArgPack((), (1, 2, 3, 4, 5), {}),
            {"x": 1, "y": 2, "*args": (3, 4, 5)},
        ),
        (
            lambda x, **kw: None,
            ArgPack((), (), {"x": 10, "y": 20, "z": 30}),
            {"x": 10, "**kw": {"y": 20, "z": 30}},
        ),
        (
            lambda x, *args, **kw: None,
            ArgPack((), (1, 2, 3, 4), {"y": 20, "z": 30}),
            {"x": 1, "*args": (2, 3, 4), "**kw": {"y": 20, "z": 30}},
        ),
    ]
    + test_make_labels_py3,
)
def test_make_labels(f, pargs, merged):
    kwargified = pargs.labels(Callable(f))
    assert kwargified == merged


@pytest.mark.parametrize(
    "f,pargs,exc",
    [
        (lambda: None, ArgPack((), (1, 2), {}), TypeError),
        (lambda x, y: None, ArgPack((), (2, 3), {"x": 1}), TypeError),
        (lambda x, y, z=30: None, ArgPack((), (1,), {}), TypeError),
        (lambda x, y, z=30: None, ArgPack((), (1,), {"x": 2}), TypeError),
    ],
)
def test_make_labels_exc(f, pargs, exc):
    with pytest.raises(exc):
        pargs.labels(Callable(f))


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

    class A:
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
