
from ring import coder


def test_coder_json():
    assert b'1' == coder.json.encode(1)
    assert 1 == coder.json.decode(b'1')

    assert b'{"x": 1}' == coder.json.encode({'x': 1})
    assert {'x': 1} == coder.json.decode(b'{"x": 1}')