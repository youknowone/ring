
import asyncio
from ring.func_base import BaseInterface, NotFound, factory
from ring.func_asyncio import wrapper_class

import pytest


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
        client, key_prefix, time=0, coder=None, ignorable_keys=None,
        interface=DoubleCacheInterface):
    from ring.func_asyncio import DictImpl

    return factory(
        client, key_prefix=key_prefix, wrapper_class=wrapper_class,
        interface=interface, storage_implementation=DictImpl,
        miss_value=None, expire_default=time, coder=coder,
        ignorable_keys=ignorable_keys)


@pytest.mark.asyncio
def test_x():
    storage = {}

    f_value = 0

    @doublecache(storage, key_prefix='f', time=10)
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
