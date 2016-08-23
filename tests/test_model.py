
from __future__ import absolute_import

from ring.storage import DictStorage
from ring.ring import Model, ModelMixin


def test_model_mixin():

    storage = DictStorage({})
    user_model = Model(storage)

    @user_model.bind
    class User(ModelMixin):

        __ring_storage__ = storage
        __ring_key_format__ = 'user:{id}:{_tag}'

        def __init__(self, id):
            self.id = id

        @user_model.ring(tag='json')
        def json(self):
            return {
                'type': 'user',
                'id': self.id,
            }

    user = User(42)

    assert user.json() == {  # gen
        'type': 'user',
        'id': 42,
    }
    assert storage.get("user:42:{'_name': 'json'}").value == user.json()

    user.json.expire()  # expire by rich method
    assert storage.get('user:42:json').value is None

    assert user.json()  # regen

    user.ring(tag='json').expire()  # expire by tag
    assert storage.get('user:42:json').value is None

    assert user.json()  # regen

    user.expire()   # expire by model
    assert storage.get('user:42:json').value is None


"""
def test_model_subscription():

    storage = DictStorage()
    user_model = Model('user:{user_id}:{_tag}')

    @user_model.bind
    class User(object):

        def __init__(self, id):
            self.id = id

        @property
        @user_model.ring(tag='json', storage=storage)
        def json(self):
            return {
                'type': 'user',
                'id': self.id,
            }

    user = User(42)
    assert user.json == {
        'type': 'user',
        'id': 42,
    }
    assert storage.get('user:42:json').value == user.json

    user_model.ring(tag='json', storage=storage).expire(id=id)
    assert storage.get('user:42:json').value is None
"""
