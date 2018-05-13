
from ring.callable import Callable

import pytest


@pytest.mark.parametrize('f,args,kwargs,merged', [
    (lambda x, *args, y=10, **kw: None, (1,), {}, dict(x=1, args=(), y=10, kw={})),
    (lambda x, *, y, z=20: None, (1,), dict(y=10), dict(x=1, y=10, z=20)),
])
def test_kwargify_py3(f, args, kwargs, merged):
    kwargified = Callable(f).kwargify(args, kwargs)
    print(kwargified)
    print(merged)
    assert kwargified == merged, (kwargified, merged)


@pytest.mark.parametrize('f,args,kwargs,exc', [
    (lambda x, *args, y=30: None, (2), {'x': 1}, TypeError),
    (lambda x, *, y, z=20: None, (1,), {}, TypeError),
    (lambda x, *, z=20: None, (1,), {'w': 2}, TypeError),
])
def test_kwargify_exc_py3(f, args, kwargs, exc):
    with pytest.raises(exc):
        Callable(f).kwargify(args, kwargs)
