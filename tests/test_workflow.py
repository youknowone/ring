
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

        @ring.dict(cache)
        def data(self):
            return self._data.copy()

        @ring.dict(cache)
        def child(self, n):
            return {'child_id': self.user_id * 10000 + n}

    u1 = User(user_id=42, name='User 1')

    # get cache or none
    assert None is u1.data.get()

    # get cache or create cache
    assert u1.data() == {'user_id': 42, 'name': 'User 1'}

    # do you want to access to cache directly?
    key = u1.data.key()
    assert u1.data() == cache[key]  # whenever you want!

    u1._data['name'] = 'User renamed'
    assert u1.data() == {'user_id': 42, 'name': 'User 1'}  # still cached

    # force to update
    assert u1.data.update() == {'user_id': 42, 'name': 'User renamed'}

    # shared by user_id
    u2 = User(user_id=42)
    assert u1 != u2
    assert u1.data.execute() != u2.data.execute()  # value is different
    assert u1.data() == u2.data()  # but sharing the cache

    # delete
    assert u1.data.get()
    u1.data.delete()
    assert not u1.data.get()

    # parametrized calling!
    assert {'child_id': 420007} == u1.child(7)
    assert {'child_id': 420007} == u1.child(n=7)  # support keyword parameter too
    assert u1.child.key(7) == u1.child.key(n=7)  # generated cache keys are also same

    # but distinguished from other parameters
    assert u1.child.key(1) != u1.child.key(2)
