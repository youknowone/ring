import sys

import ring
from ring.coder import (
    Registry, Coder, JsonCoder, coderize, registry as default_registry)

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

    @ring.memcache(mc, coder='pickle')
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


def test_ring_bare_coder():
    @ring.dict({}, coder=JsonCoder)
    def f():
        return 10

    assert f() == 10


if sys.version_info >= (3, 7):
    from tests._test_module_py37 import DataClass

    def test_dataclass_coder():
        coder = default_registry.get('dataclass')
        dataclass = DataClass('name', 1, {'test': 1})
        encoded_dataclass = coder.encode(dataclass)
        assert b'{"name": "DataClass", "fields": {"name": "name", "my_int": 1, "my_dict": {"test": 1}}}' == encoded_dataclass
        decoded_dataclass = coder.decode(encoded_dataclass)
        assert 'DataClass' == type(decoded_dataclass).__name__
        assert decoded_dataclass.name == 'name'
        assert decoded_dataclass.my_int == 1
        assert decoded_dataclass.my_dict == {'test': 1}


def test_unexisting_coder():
    cache = {}

    with pytest.raises(TypeError):
        @ring.dict(cache, coder='messed-up')
        def f():
            pass


@pytest.mark.parametrize('raw_coder', [
    JsonCoder,
])
def test_coderize(raw_coder):
    assert raw_coder
    assert isinstance(coderize(raw_coder), Coder)


def test_invalid_coderize():
    with pytest.raises(TypeError):
        coderize(1)
