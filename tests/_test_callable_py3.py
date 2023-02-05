import asyncio
from typing import Any, Optional
from ring.callable import Callable
from ring.func.base import ArgPack

import pytest


@pytest.mark.parametrize(
    "f,pargs,merged",
    [
        (
            lambda x, *args, y=10, **kw: None,
            ArgPack((), (1,), {}),
            {"x": 1, "*args": (), "y": 10, "**kw": {}},
        ),
        (
            lambda x, *, y, z=20: None,
            ArgPack((), (1,), dict(y=10)),
            {"x": 1, "y": 10, "z": 20},
        ),
    ],
)
def test_make_labels_py3(f, pargs, merged):
    kwargified = pargs.labels(Callable(f))
    assert kwargified == merged, (kwargified, merged)


@pytest.mark.parametrize(
    "f,pargs,exc",
    [
        (lambda x, *args, y=30: None, ArgPack((), (2), {"x": 1}), TypeError),
        (lambda x, *, y, z=20: None, ArgPack((), (1,), {}), TypeError),
        (lambda x, *, z=20: None, ArgPack((), (1,), {"w": 2}), TypeError),
    ],
)
def test_make_labels_exc_py3(f, pargs, exc):
    with pytest.raises(exc):
        pargs.labels(Callable(f))


def test_annotations():
    def f(a: int, b: str, *c, d: Any = 10, **e) -> Optional[float]:
        pass

    c = Callable(f)
    assert c.annotations == {"a": int, "b": str, "d": Any, "return": Optional[float]}


def test_code():
    def f(a):
        pass  # noqa

    assert Callable(f).code.co_name == "f"

    h = asyncio.coroutine(f)
    assert Callable(h).code.co_name == "f"
