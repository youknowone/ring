
from cachain.storage import DictStorage
from cachain.ingredient import Ring


import pytest


@pytest.fixture
def fx_ring():
    storage = DictStorage({})
    ring = Ring(storage, 'user_id:{user_id}')
    return ring


def test_ring_get_set(fx_ring):
    assert fx_ring.get({'user_id': 1}) is None
    fx_ring.set(lambda user_id: 100, {'user_id': 1})


def test_ring_get_or_set(fx_ring):
    assert fx_ring.get({'user_id': 1}) is None
    assert fx_ring.get_or_set(lambda user_id: 100, {'user_id': 1}) == 100
    assert fx_ring.get({'user_id': 1}) == 100


