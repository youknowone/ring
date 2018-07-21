import six
import ring
from ring.key import FormatKey, CallableKey

import pytest


@pytest.fixture(scope='session')
def format_key():
    return FormatKey('prefix:{a}:{b}:{c040}')


@pytest.fixture(scope='session')
def callable_key():
    return CallableKey(lambda a, b, c040: None)


@pytest.fixture(params=[
    pytest.lazy_fixture('format_key'),
    pytest.lazy_fixture('callable_key'),
])
def ring_key(request):
    return request.param


def test_provider_keys(ring_key):
    provider_keys_set = {'a', 'b', 'c040'}
    pkeys = ring_key.provider_keys_set
    assert isinstance(pkeys, frozenset)
    assert pkeys == ring_key.provider_keys_set == provider_keys_set


def test_key_build(ring_key):
    assert ring_key.build({'a': 1, 'b': 2, 'c040': 3}).endswith(':1:2:3')

    with pytest.raises(KeyError):
        ring_key.build({'a': 1, 'b': 2, 'c': 3})
    with pytest.raises(KeyError):
        ring_key.build({'a': 1, 'b': 2})


def test_key_repr(ring_key):
    assert repr(ring_key)


def test_callable_key():
    key = CallableKey((lambda cls, b, c040: None), format_prefix='', ignorable_keys=['cls'])
    assert key.format == ':{b}:{c040}'


def test_classmethod_key():
    cache = {}

    class A(object):

        @ring.dict(cache)
        @classmethod
        def f(cls):
            return 10

    class B(A):
        pass

    assert A.f.key().endswith('.A.f:A'), A.f.key()
    if six.PY3:
        assert B.f.key().endswith('.A.f:B'), B.f.key()
    else:  # py2 has a problem
        assert B.f.key().endswith('.B.f:B'), B.f.key()

    a = A()
    b = B()

    assert a.f.key().endswith('.A.f:A'), a.f.key()
    if six.PY3:
        assert b.f.key().endswith('.A.f:B'), b.f.key()
    else:  # py2 has a problem
        assert b.f.key().endswith('.B.f:B'), b.f.key()

    assert A.f.key() == a.f.key()
    assert B.f.key() == b.f.key()


def test_unexisting_ring_key():
    cache = {}

    class A(object):
        @ring.dict(cache)
        def f(self):
            return 0

    a = A()
    with pytest.raises(TypeError):
        a.f()


@pytest.mark.parametrize('v', (None, Ellipsis))
def test_singleton(v):

    @ring.dict({})
    def f(a, b=v):
        return a, b

    assert f(1) == (1, v)
    assert f(2) == (2, v)
    assert f(1, 1) == (1, 1)
    assert f(1, 2) == (1, 2)
    assert f(1) == (1, v)


def test_basic_ignorable_key():
    @ring.dict({}, ignorable_keys=['ignorable'])
    def f(n, ignorable):
        return n + ignorable

    # the actual funtion can be different
    assert f.execute(10, 5) != f.execute(10, 10)
    # but key must be same
    assert f.key(10, 'ignorable') == f.key(10, 'must be not considered')

    # not ring-key compatible object
    class A(object):
        pass

    assert f.key(10, A())  # ignorable key must not affect key generation
