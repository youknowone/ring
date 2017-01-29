
import ring


class Object(object):

    def __init__(self, **kwargs):
        self._data = kwargs

    def __getattr__(self, key):
        if key in self._data:
            return self._data[key]
        return getattr(super(Object, self), key)


def test_workflow():
    cache = {}

    class User(Object):
        def __ring_key__(self):
            return 'User{self.user_id}'.format(self=self)

        @ring.func.dict(cache)
        def data(self):
            return self._data

    class Asset(Object):
        def __ring_key__(self):
            return '{self.user_id}:{self.asset_id}'.format(self=self)

    u1 = User(user_id=10, name='User 1')
    assert {'user_id': 10, 'name': 'User 1'} == u1.data()
    assert u1.data.key() == ':User10'
