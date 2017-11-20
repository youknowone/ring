
import ring
from ring.coder import registry

import pytest


def test_coder_registry():
    error_coder = None, None
    registry.register('_error', error_coder)

    assert registry.get('_error') == (None, None)


def test_coder_json():

    encode, decode = registry.get('json')

    assert b'1' == encode(1)
    assert 1 == decode(b'1')

    assert b'{"x": 1}' == encode({'x': 1})
    assert {'x': 1} == decode(b'{"x": 1}')


def test_coder_pickle():
    import memcache
    import datetime

    encode, decode = registry.get('pickle')
    mc = memcache.Client(['127.0.0.1:11211'])

    @ring.func.memcache(mc, coder='pickle')
    def now():
        return datetime.datetime.now()

    now.delete()

    dt_now = now()
    direct_data = mc.get(now.key())
    assert direct_data

    encoded_data = encode(dt_now)
    assert encoded_data == direct_data

    decoded_data = decode(encoded_data)
    assert decoded_data == dt_now


def test_unexisting_coder():
    cache = {}

    with pytest.raises(TypeError):
        @ring.func.dict(cache, coder='messed-up')
        def f():
            pass
