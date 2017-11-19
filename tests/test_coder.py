
import ring
from ring.coder import JsonCoder, PickleCoder
from ring.coder import registry

import pytest


def test_coder_registry():

    registry.register('json', JsonCoder)
    registry.register('pickle', PickleCoder)

    assert registry.get('json') == ring.coder.JsonCoder
    assert registry.get('pickle') == ring.coder.PickleCoder


def test_coder_json():

    registry.register('json', JsonCoder)

    assert b'1' == registry.json.encode(1)
    assert 1 == registry.json.decode(b'1')

    assert b'{"x": 1}' == registry.json.encode({'x': 1})
    assert {'x': 1} == registry.json.decode(b'{"x": 1}')


def test_coder_pickle():
    import memcache
    import datetime

    mc = memcache.Client(['127.0.0.1:11211'])

    registry.register('pickle', PickleCoder)

    @ring.func.memcache(mc, coder='pickle')
    def now():
        return datetime.datetime.now()

    now.delete()

    dt_now = now()
    direct_data = mc.get(now.key())
    assert direct_data

    encoded_data = registry.pickle.encode(dt_now)
    assert encoded_data == direct_data

    decoded_data = registry.pickle.decode(encoded_data)
    assert decoded_data == dt_now


def test_unexisting_coder():
    cache = {}

    with pytest.raises(TypeError):
        @ring.func.dict(cache, coder='messed-up')
        def f():
            pass
