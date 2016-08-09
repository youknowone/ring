
from ring.storage import DictStorage
from ring.ring import Ring


import pytest


@pytest.fixture
def fx_ring():
    storage = DictStorage({})
    ring = Ring(storage, 'user:{user_id}')
    return ring


@pytest.fixture
def fx_ding(fx_ring):
    storage = DictStorage({})
    ring = Ring(storage, 'asset:{user_id}:{asset_id}')
    return ring


def test_ring_get_set(fx_ring):
    assert fx_ring.get(user_id=1) is None
    fx_ring.set(lambda user_id: 100, user_id=1)
    assert fx_ring.get(user_id=1) == 100
    fx_ring.delete(user_id=1)
    assert fx_ring.get(user_id=1) is None


def test_ring_get_or_set(fx_ring):
    assert fx_ring.get(user_id=1) is None
    assert fx_ring.get_or_set(lambda user_id: 100, user_id=1) == 100
    assert fx_ring.get(user_id=1) == 100
    fx_ring.delete(user_id=1)
    assert fx_ring.get(user_id=1) is None


def test_decorator(fx_ring):
    history = []

    @fx_ring(expire=None)
    def build_data(user_id):
        history.append(user_id)
        return {
            'id': user_id,
            'name': 'Name {}'.format(user_id),
        }

    u1 = build_data(user_id=1)
    assert history == [1]
    u2 = build_data(1)
    assert history == [1]
    assert u1 == u2 == {
        'id': 1,
        'name': 'Name 1'
    }
    u3 = build_data(3)
    assert history == [1, 3]
    u4 = build_data(3)
    assert history == [1, 3]
    assert u3 == u4 == {
        'id': 3,
        'name': 'Name 3'
    }
    u5 = build_data(1)
    assert u1 == u5


def test_link(fx_ring, fx_ding):

    fx_ring.set(lambda user_id: user_id, user_id=1)
    fx_ding.set(lambda user_id, asset_id: user_id * 1000 + asset_id, user_id=1, asset_id=1)

    assert fx_ring.get(user_id=1) == 1
    assert fx_ding.get(user_id=1, asset_id=1) == 1001

    fx_ding.link(fx_ring, ['user_id'])

    fx_ding.set(1003, user_id=1, asset_id=1)
    assert fx_ring.get(user_id=1) is None
    assert fx_ding.get(user_id=1, asset_id=1) == 1001
