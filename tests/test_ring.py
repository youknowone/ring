
import ring
import pytest
from .test_func_sync import pythonmemcache_client

__all__ = ('pythonmemcache_client', )


class hybridmethod(object):

    def __init__(self, func):
        self.__func__ = func

    def __get__(self, obj, type=None):
        bound = obj if obj is not None else type
        return self.__func__.__get__(bound, type)


class A(object):

    v = -10

    def __init__(self, v):
        self.v = v

    def __ring_key__(self):
        return str(self.v)

    @ring.dict({})
    def x(self):
        return self.v

    @ring.dict({})
    @hybridmethod
    def h(self):
        return self.v

    @ring.dict({})
    @property
    def p(self):
        return self.v

    @ring.dict({})
    @staticmethod
    def s(v):
        return v


def test_ring_wrapper():
    a = A(10)
    b = A(20)
    print(a.x.key())
    print(b.x.key())
    print(a.x.storage)
    print(b.x.storage)
    assert a.x() == 10
    assert b.x() == 20
    assert a.x() == 10
    assert b.x() == 20
    assert a.s(10) == 10
    assert a.s(20) == 20


def test_custom_method():
    assert A.h() == -10
    assert A(10).h() == 10


def test_ring_property():
    a = A(15)
    assert a.p == 15


@pytest.mark.parametrize('value', [
    1,
    0,
    True,
    False,
    u'str',
    b'bytes',
    ['list', 'with', 'values'],
    {'dict': 'also', 'matters': '!'},
    {'set', 'should', 'be', 'ordered'},
])
def test_ring_key(value):
    # test only with real cache backends. dict doesn't help this test
    @ring.memcache(pythonmemcache_client, expire=1)
    def simple(key):
        return key

    assert simple(value) == value  # cache miss
    assert simple(value) == value  # cache hit


def test_proxy_repr():

    @ring.dict({})
    def f():
        pass

    assert repr(ring.dict)
    assert repr(ring.dict({}))
    assert repr(f)


def test_proxy_cache():

    dring = ring.dict({})

    @dring
    def f1():
        pass

    @dring
    def f2():
        pass


def test_package_version():
    parts = ring.__version__.split('.')
    assert len(parts) == 3
    assert parts[0] == '0'
