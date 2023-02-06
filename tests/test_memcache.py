# coding: utf-8
import ring

import pytest
from .test_func_sync import memcache_client

__all__ = ("memcache_client",)


try:
    import pylibmc
except ImportError:
    pylibmc_client = None
else:
    pylibmc_client = pylibmc.Client(["127.0.0.1"])


def test_memcache_key(memcache_client):
    if memcache_client is None:
        pytest.skip()

    @ring.memcache(memcache_client, "ring-test")
    def f(a, b):
        r = a + b
        if isinstance(r, str):
            r = r.encode("utf-8")
        return r

    assert f.key("a", "b") == "ring-test:a:b"
    assert f.key("a", "b with space") != "ring-test:a:b with space"
    assert f.key("a", "b with 문자") != "ring-test:a:b with 문자"

    f.delete(1, 2)
    assert None is f.get(1, 2)
    assert 3 == int(f(1, b=2))
    assert 3 == int(f.get(1, 2))

    f.delete("a", "b with space")
    assert None is f.get("a", "b with space")
    assert b"ab with space" == f("a", b="b with space")
    assert b"ab with space" == f.get("a", b="b with space")


def test_memcache(memcache_client):
    base = [0]

    @ring.memcache(memcache_client, "ring-test")
    def f(a, b):
        r = base[0] + a * 100 + b
        sr = str(r)
        if memcache_client.is_binary:
            sr = sr.encode("utf-8")
        return sr

    f.delete(8, 6)
    assert f.key(8, 6) == "ring-test:8:6"

    base[0] = 10000
    assert None is f.get(8, b=6)
    assert 10806 == int(f(8, b=6))
    assert 10806 == int(memcache_client.get(f.key(8, 6)))


def test_memcache_multi(memcache_client):
    @ring.memcache(memcache_client, "ring-test", coder="json")
    def f(a, b):
        return a * 100 + b

    mv = f.execute_many(
        {"a": 1, "b": 2},
        (1, 4),
        (5, 1),
    )
    assert mv == [102, 104, 501]

    f.delete_many(
        {"a": 1, "b": 2},
        (1, 4),
        (5, 1),
    )

    mv = f.get_many(
        {"a": 1, "b": 2},
        {"a": 1, "b": 4},
        (5, 1),
    )
    assert mv == [None, None, None]

    mv = f.update_many(
        {"a": 1, "b": 2},
        (5, 1),
    )
    assert mv == [102, 501]

    mv = f.get_many(
        (1, 2),
        (1, 4),
        (5, 1),
    )
    assert mv == [102, None, 501]

    f.set_many(
        (
            (1, 2),
            (1, 4),
        ),
        (
            503,
            716,
        ),
    )
    mv = f.get_many(
        (1, 2),
        (1, 4),
        (5, 1),
    )
    assert mv == [503, 716, 501]
    f.delete(1, 4)
    mv = f.get_or_update_many(
        (1, 2),
        (1, 4),
        (5, 1),
    )
    assert mv == [503, 104, 501]

    with pytest.raises(AttributeError):
        f.touch_many()

    with pytest.raises(TypeError):
        f.delete_many([1, 4])

    with pytest.raises(AttributeError):
        f.has_many()
