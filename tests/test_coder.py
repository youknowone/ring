
import ring
import ring.coder

import pytest


def test_coder_json():
    assert b'1' == ring.coder.json.encode(1)
    assert 1 == ring.coder.json.decode(b'1')

    assert b'{"x": 1}' == ring.coder.json.encode({'x': 1})
    assert {'x': 1} == ring.coder.json.decode(b'{"x": 1}')


def test_coder_pickle():
    import memcache
    import datetime

    mc = memcache.Client(['127.0.0.1:11211'])

    @ring.func.memcache(mc, coder='pickle')
    def now():
        return datetime.datetime.now()

    dt_now = now()
    direct_data = mc.get(now.key())
    assert direct_data

    encoded_data = ring.coder.pickle.encode(dt_now)
    assert encoded_data == direct_data

    decoded_data = ring.coder.pickle.decode(encoded_data)
    assert decoded_data == dt_now


def test_unexisting_coder():
    cache = {}

    with pytest.raises(TypeError):
        @ring.func.dict(cache, coder='messed-up')
        def f():
            pass
