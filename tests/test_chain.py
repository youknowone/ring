

'''
from ring.storage import DictStorage
from ring.ring import CallableRing, Link


import pytest


@pytest.fixture
def fx_ring():
    storage = DictStorage({})
    ring = CallableRing(storage, 'user:{user_id}')
    return ring


@pytest.fixture
def fx_ding(fx_ring):
    storage = DictStorage({})
    ring = CallableRing(storage, 'asset:{user_id}:{asset_id}')
    return ring


def test_ring_get_update(fx_ring):
    assert fx_ring.get(user_id=1) is None
    fx_ring.update(lambda user_id: 100, user_id=1)
    assert fx_ring.get(user_id=1) == 100
    fx_ring.expire(user_id=1)
    assert fx_ring.get(user_id=1) is None


def test_ring_get_or_update(fx_ring):
    assert fx_ring.get(user_id=1) is None
    assert fx_ring.get_or_update(lambda user_id: 100, user_id=1) == 100
    assert fx_ring.get(user_id=1) == 100
    fx_ring.expire(user_id=1)
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

    fx_ring.update(lambda user_id: user_id, user_id=1)
    fx_ding.update(lambda user_id, asset_id: user_id * 1000 + asset_id, user_id=1, asset_id=1)

    assert fx_ring.get(user_id=1) == 1
    assert fx_ding.get(user_id=1, asset_id=1) == 1001

    fx_ding.link(fx_ring)
    assert Link(fx_ring) in fx_ding.direct_links[fx_ring.key.partial_keys]

    fx_ding.update(1003, user_id=1, asset_id=1)
    assert fx_ring.get(user_id=1) is None
    assert fx_ding.get(user_id=1, asset_id=1) == 1003

    fx_ring.update(2, user_id=1)

    assert fx_ring.get(user_id=1) == 2
    assert fx_ding.get(user_id=1, asset_id=1) == 1003

    fx_ding.expire(user_id=1, asset_id=1)

    assert fx_ring.get(user_id=1) is None
    assert fx_ding.get(user_id=1, asset_id=1) is None


def test_indirect_marker(fx_ring, fx_ding):
    fx_ring.indirect_link(fx_ding)
    assert Link(fx_ding) in fx_ring.indirect_links[frozenset(['user_id'])]
    assert Link(fx_ring) in fx_ding.incoming_links[frozenset(['user_id'])]


def test_indirect_link(fx_ring, fx_ding):

    fx_ring.update(lambda user_id: user_id, user_id=1)
    fx_ding.update(lambda user_id, asset_id: user_id * 1000 + asset_id, user_id=1, asset_id=1)
    fx_ding.update(lambda user_id, asset_id: user_id * 1000 + asset_id, user_id=1, asset_id=2)
    fx_ding.update(lambda user_id, asset_id: user_id * 1000 + asset_id, user_id=2, asset_id=1)

    assert fx_ring.get(user_id=1) == 1
    assert fx_ding.get(user_id=1, asset_id=1) == 1001
    assert fx_ding.get(user_id=1, asset_id=2) == 1002
    assert fx_ding.get(user_id=2, asset_id=1) == 2001

    fx_ring.indirect_link(fx_ding)

    fx_ring.update(2, user_id=1)
    assert fx_ring.get(user_id=1) == 2
    assert fx_ding.get(user_id=1, asset_id=1) is None
    assert fx_ding.get(user_id=1, asset_id=2) is None
    assert fx_ding.get(user_id=2, asset_id=1) == 2001

    fx_ring.update(lambda user_id: user_id, user_id=1)
    fx_ding.update(lambda user_id, asset_id: user_id * 1000 + asset_id, user_id=1, asset_id=1)
    fx_ding.update(lambda user_id, asset_id: user_id * 1000 + asset_id, user_id=1, asset_id=2)

    fx_ring.expire(user_id=1)
    assert fx_ring.get(user_id=1) is None
    assert fx_ding.get(user_id=1, asset_id=1) is None
    assert fx_ding.get(user_id=1, asset_id=2) is None
    assert fx_ding.get(user_id=2, asset_id=1) == 2001

    fx_ring.expire(user_id=2)
    assert fx_ding.get(user_id=2, asset_id=1) is None


def test_link_workflow(fx_ring, fx_ding):
    fx_ding.link(fx_ring)

    asset_names = [
        None, 'ring', 'ding', 'dong'
    ]

    history = []

    @fx_ring()
    def user_data(user_id):
        history.append('user:{}'.format(user_id))
        return {
            'id': user_id,
            'name': 'Name {}'.format(user_id),
            'assets': [
                asset_data(user_id, 1),
                asset_data(user_id, 2),
                asset_data(user_id, 3),
            ]
        }

    @fx_ding()
    def asset_data(user_id, asset_id):
        history.append('asset:{}:{}'.format(user_id, asset_id))
        return {
            'id': asset_id,
            'user_id': user_id,
            'name': asset_names[asset_id],
        }

    assert history == []

    # generate cache for user 1 and its assets
    u1 = user_data(1)
    assert [asset['name'] for asset in u1['assets']] == ['ring', 'ding', 'dong']
    assert history == ['user:1', 'asset:1:1', 'asset:1:2', 'asset:1:3']

    # generate cache for user 2 and its assets
    asset_names[3] = 'doh!'
    u2 = user_data(2)
    assert [asset['name'] for asset in u2['assets']] == ['ring', 'ding', 'doh!']
    assert history == ['user:1', 'asset:1:1', 'asset:1:2', 'asset:1:3', 'user:2', 'asset:2:1', 'asset:2:2', 'asset:2:3']

    # reuse cache for user 1 and its asset - the names isn't changed
    u1_x = user_data(1)
    assert [asset['name'] for asset in u1_x['assets']] == ['ring', 'ding', 'dong']
    assert u1 == u1_x
    assert history == ['user:1', 'asset:1:1', 'asset:1:2', 'asset:1:3', 'user:2', 'asset:2:1', 'asset:2:2', 'asset:2:3']

    # but because we changed asset name of 3, it must be notified
    fx_ding.expire(user_id=1, asset_id=3)

    # then u1 will be also expired, but not about asset1 and asset2
    u1 = user_data(1)
    assert [asset['name'] for asset in u1['assets']] == ['ring', 'ding', 'doh!']
    assert history[-5:] == ['asset:2:1', 'asset:2:2', 'asset:2:3', 'user:1', 'asset:1:3']

    # what if only user changed - it will not affect any assets. only user is
    # updated
    fx_ring.expire(user_id=1)
    u1 = user_data(1)
    assert [asset['name'] for asset in u1['assets']] == ['ring', 'ding', 'doh!']
    assert history[-5:] == ['asset:2:2', 'asset:2:3', 'user:1', 'asset:1:3', 'user:1']
'''
