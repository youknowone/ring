
import asyncio
import pytest
import ring.func_sync
from ring.func_base import BaseInterface, NotFound, factory
from ring.func_asyncio import wrapper_class


class DoubleCacheInterface(BaseInterface):

    def _key2(self, args, kwargs):
        return self._key(args, kwargs) + ':back'

    @asyncio.coroutine
    def _get(self, args, kwargs):
        key1 = self._key(args, kwargs)
        key2 = self._key2(args, kwargs)

        result = ...
        for key in [key1, key2]:
            try:
                result = yield from self._p_get(key)
            except NotFound:
                continue
            else:
                break
        if result is ...:
            result = self._miss_value
        return result

    @asyncio.coroutine
    def _update(self, args, kwargs):
        key = self._key(args, kwargs)
        key2 = self._key2(args, kwargs)
        result = yield from self._execute(args, kwargs)
        yield from self._p_set(key, result)
        yield from self._p_set(key2, result, None)
        return result

    @asyncio.coroutine
    def _get_or_update(self, args, kwargs):
        key = self._key(args, kwargs)
        key2 = self._key2(args, kwargs)
        try:
            result = yield from self._p_get(key)
        except NotFound:
            try:
                result = yield from self._execute(args, kwargs)
            except Exception as e:
                try:
                    result = yield from self._p_get(key2)
                except NotFound:
                    pass
                else:
                    return result
                raise
            else:
                yield from self._p_set(key, result)
                yield from self._p_set(key2, result, None)
        return result

    @asyncio.coroutine
    def _delete(self, args, kwargs):
        key = self._key(args, kwargs)
        key2 = self._key2(args, kwargs)
        yield from self._p_delete(key)
        yield from self._p_delete(key2)

    @asyncio.coroutine
    def _touch(self, args, kwargs):
        key = self._key(args, kwargs)
        key2 = self._key(args, kwargs)
        yield from self._p_touch(key)
        yield from self._p_touch(key2)


def doublecache(
        client, key_prefix, expire=0, coder=None, ignorable_keys=None,
        interface=DoubleCacheInterface):
    from ring.func_asyncio import DictImpl

    return factory(
        client, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=interface, storage_implementation=DictImpl,
        miss_value=None, expire_default=expire, coder=coder,
        ignorable_keys=ignorable_keys)


@pytest.mark.asyncio
def test_x():
    storage = {}

    f_value = 0

    @doublecache(storage, key_prefix='f', expire=10)
    @asyncio.coroutine
    def f():
        nonlocal f_value
        if f_value < 0:
            raise Exception
        return f_value

    assert storage == {}
    assert 0 == (yield from f())
    assert 'f' in storage
    assert 'f:back' in storage
    assert 0 == (yield from f.get())

    del storage['f']
    assert 0 == (yield from f.get())
    assert len(storage) == 1

    f_value = -1

    assert 0 == (yield from f.get())
    assert len(storage) == 1
    assert 0 == (yield from f())
    assert len(storage) == 1

    yield from f.delete()
    assert storage == {}

    assert None is (yield from f.get())

    f_value = 2
    yield from f.update()
    assert 2 == (yield from f())

    storage['f'] = storage['f'][0], 1
    assert 1 == (yield from f.get())
    assert 1 == (yield from f())
    del storage['f']
    f_value = 3
    assert 2 == (yield from f.get())
    assert 3 == (yield from f())
    assert 3 == (yield from f.get())


def test_coder_func():

    storage = {}

    @ring.func.dict(storage)
    def f(a):
        return a

    encoded_value = f.encode('value')
    decoded_value = f.decode(encoded_value)
    assert encoded_value == decoded_value

    assert f('10') == '10'
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
