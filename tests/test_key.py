import ring
from ring.key import FormatKey, CallableKey

import pytest


@pytest.mark.parametrize(['key', 'provider_keys_set'], [
    (FormatKey('prefix:{a}:{b}:{c040}'), {'a', 'b', 'c040'}),
    (CallableKey(lambda a, b, c040: None), {'a', 'b', 'c040'}),
])
def test_provider_keys(key, provider_keys_set):
    pkeys = key.provider_keys_set
    assert isinstance(pkeys, frozenset)
    assert pkeys == key.provider_keys_set == provider_keys_set


def test_callable_key():
    key = CallableKey((lambda cls, b, c040: None), format_prefix='', ignorable_keys=['cls'])
    assert key.format == ':{b}:{c040}'


def test_classmethod_key():
    cache = {}

    class A(object):

        @ring.func.dict(cache)
        @classmethod
        def f(cls):
            return 10

    class B(A):
        pass

    assert A.f.key().endswith('.A.f:A'), A.f.key()
    # assert B.f.key().endswith('.A.f:B'), B.f.key() -- TODO


def test_unexisting_ring_key():
    cache = {}

    class A(object):
        @ring.func.dict(cache)
        def f(self):
            return 0

    a = A()
    with pytest.raises(TypeError):
        a.f()
