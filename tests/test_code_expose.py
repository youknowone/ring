
import ring

def test_coder_func():

    storage = {}

    @ring.func.dict(storage)
    def f(a):
        return a

    encoded_value = f.encode('value')
    decoded_value = f.decode(encoded_value)
    assert encoded_value == decoded_value

    f('10')
    raw_value = storage.get(f.key('10'))  # raw value
    value = f.decode(raw_value)
    assert f.get('10') == value[1]


def test_coder_method():

    storage = {}

    class Object(object):

        def __init__(self, **kwargs):
            self._data = kwargs

        def __getattr__(self, key):
            if key in self._data:
                return self._data[key]
            return getattr(super(Object, self), key)


    class User(Object):
        def __ring_key__(self):
            return 'User{self.user_id}'.format(self=self)

        @ring.func.dict(storage)
        def data(self):
            return self._data.copy()


    u1 = User(user_id=42, name='User 1')
    u1.data()

    encoded_value = u1.data.encode(u1.data.key())
    decoded_value = u1.data.decode(encoded_value)
    assert encoded_value == decoded_value

    raw_value = storage.get(u1.data.key())
    value = u1.data.decode(raw_value)
    assert u1.data.get() == value[1]
