
from cachain.storage import DictStorage
from cachain.ingredient import Ring


import pytest


@pytest.fixture
def fx_ring():
    storage = DictStorage({})
    ring = Ring(storage, 'user_id:{user_id}')
    return ring


def test_ring_get_set(fx_ring):
    assert fx_ring.get(user_id=1) is None
    fx_ring.set(lambda user_id: 100, user_id=1)


def test_ring_get_or_set(fx_ring):
    assert fx_ring.get(user_id=1) is None
    assert fx_ring.get_or_set(lambda user_id: 100, user_id=1) == 100
    assert fx_ring.get(user_id=1) == 100


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
