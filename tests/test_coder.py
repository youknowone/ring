
import ring
import ring.coder
import pickle

import pytest


def test_coder_json():
    assert b'1' == ring.coder.json.encode(1)
    assert 1 == ring.coder.json.decode(b'1')

    assert b'{"x": 1}' == ring.coder.json.encode({'x': 1})
    assert {'x': 1} == ring.coder.json.decode(b'{"x": 1}')


def test_unexisting_coder():
    cache = {}

    with pytest.raises(TypeError):
        @ring.func.dict(cache, coder='messed-up')
        def f():
            pass


def test_coder_pickle():
    assert pickle.dumps(1, 0) == ring.coder.pickle.encode(1)
    assert pickle.loads(pickle.dumps(1, 0)) == ring.coder.pickle.decode(ring.coder.pickle.encode(1))

    assert pickle.dumps({'x': 1}, 0) == ring.coder.pickle.encode({'x': 1})
    assert pickle.loads(pickle.dumps({'x': 1}, 0)) == ring.coder.pickle.decode(ring.coder.pickle.encode({'x': 1}))
