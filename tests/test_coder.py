
import ring
from ring.coder import Registry, Coder, registry as default_registry

import pytest


def test_coder_registry():
    registry = Registry()

    error_coder = None, None
    registry.register('_error', error_coder)

    assert registry.get('_error') == (None, None)

    tuple_coder = lambda x: x, lambda x: x  # noqa
    registry.register('tuple', tuple_coder)

    class NewStaticCoder(Coder):
        @staticmethod
        def encode(d):
            return d

        @staticmethod
        def decode(d):
            return d

    registry.register('new_static', NewStaticCoder)
    registry.register('new_static_obj', NewStaticCoder())

    class NewCoder(Coder):
        def encode(self, x):
            return x

        def decode(self, x):
            return x

    registry.register('new_obj', NewCoder())


def test_coder_json():

    coder = default_registry.get('json')

    assert b'1' == coder.encode(1)
    assert 1 == coder.decode(b'1')

    assert b'{"x": 1}' == coder.encode({'x': 1})
    assert {'x': 1} == coder.decode(b'{"x": 1}')


def test_coder_pickle():
    import memcache
    import datetime

    coder = default_registry.get('pickle')
    mc = memcache.Client(['127.0.0.1:11211'])

    @ring.func.memcache(mc, coder='pickle')
    def now():
        return datetime.datetime.now()

    now.delete()

    dt_now = now()
    direct_data = mc.get(now.key())
    assert direct_data

    encoded_data = coder.encode(dt_now)
    assert encoded_data == direct_data

    decoded_data = coder.decode(encoded_data)
    assert decoded_data == dt_now


def test_unexisting_coder():
    cache = {}

    with pytest.raises(TypeError):
        @ring.func.dict(cache, coder='messed-up')
        def f():
            pass
