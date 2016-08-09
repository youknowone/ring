
from ring.key import FormatKey, CallableKey

import pytest


@pytest.mark.parametrize(['key', 'partial_keys'], [
    (FormatKey('prefix:{a}:{b}:{c040}'), {'a', 'b', 'c040'}),
    (CallableKey(lambda a, b, c040: None), {'a', 'b', 'c040'}),
])
def test_partial_keys(key, partial_keys):
    pkeys = key.partial_keys
    assert isinstance(pkeys, frozenset)
    assert pkeys == key.partial_keys == partial_keys
