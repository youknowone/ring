
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
