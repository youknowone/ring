
import ring


class Object(object):

    def __init__(self, **kwargs):
        self._data = kwargs

    def __getattr__(self, key):
        if key in self._data:
            return self._data[key]
        return getattr(super(Object, self), key)


def test_action_dict():
    cache = {}

    class User(Object):
        def __ring_key__(self):
            return 'User{self.user_id}'.format(self=self)

        @ring.func.dict(cache)
        def data(self):
            return self._data.copy()

    u1 = User(user_id=42, name='User 1')
    data = u1.data()
    assert data

    u1.data.run(action='delete')
    data_or_none = u1.data.get()
    assert data_or_none is None

    u1 = User(user_id=42, name='User 1')
    updated_data = u1.data.run(action="update")
    assert updated_data == data

    key = u1.data.run(name='User 1', action='key')
    direct_data = cache[key][1]
    assert data == direct_data
