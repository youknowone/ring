import pytest
import ring.func.sync
from ring.func.base import BaseUserInterface, NotFound, factory


class DoubleCacheUserInterface(BaseUserInterface):
    async def execute(self, wire, pargs):
        result = await wire.__func__(*pargs.args, **pargs.kwargs)
        return result

    def key2(self, wire, pargs):
        return self.key(wire, pargs) + ":back"

    async def get(self, wire, pargs):
        key1 = self.key(wire, pargs)
        key2 = self.key2(wire, pargs)

        result = ...
        for key in [key1, key2]:
            try:
                result = await wire._rope.storage.get(key)
            except NotFound:
                continue
            else:
                break
        if result is ...:
            result = wire._rope.config.miss_value
        return result

    async def update(self, wire, pargs):
        key1 = self.key(wire, pargs)
        key2 = self.key2(wire, pargs)

        result = await self.execute(wire, pargs)
        await wire._rope.storage.set(key1, result)
        await wire._rope.storage.set(key2, result, None)
        return result

    async def get_or_update(self, wire, pargs):
        key1 = self.key(wire, pargs)
        key2 = self.key2(wire, pargs)

        try:
            result = await wire._rope.storage.get(key1)
        except NotFound:
            try:
                result = await self.execute(wire, pargs)
            except Exception:
                try:
                    result = await wire._rope.storage.get(key2)
                except NotFound:
                    pass
                else:
                    return result
                raise
            else:
                await wire._rope.storage.set(key1, result)
                await wire._rope.storage.set(key2, result, None)
        return result

    async def delete(self, wire, pargs):
        key1 = self.key(wire, pargs)
        key2 = self.key2(wire, pargs)

        await wire._rope.storage.delete(key1)
        await wire._rope.storage.delete(key2)

    async def touch(self, wire, pargs):
        key1 = self.key(wire, pargs)
        key2 = self.key2(wire, pargs)

        await wire._rope.storage.touch(key1)
        await wire._rope.storage.touch(key2)


def doublecache(
    client, key_prefix, expire=0, coder=None, user_interface=DoubleCacheUserInterface
):
    from ring.func.sync import ExpirableDictStorage
    from ring.func.asyncio import convert_storage

    return factory(
        client,
        key_prefix=key_prefix,
        on_manufactured=None,
        user_interface=user_interface,
        storage_class=convert_storage(ExpirableDictStorage),
        miss_value=None,
        expire_default=expire,
        coder=coder,
    )


@pytest.mark.asyncio
async def test_x():
    storage = {}

    f_value = 0

    @doublecache(storage, key_prefix="f", expire=10)
    async def f():
        nonlocal f_value
        if f_value < 0:
            raise Exception
        return f_value

    assert storage == {}
    assert 0 == await f()
    assert "f" in storage
    assert "f:back" in storage
    assert 0 == await f.get()

    del storage["f"]
    assert 0 == await f.get()
    assert len(storage) == 1

    f_value = -1

    assert 0 == await f.get()
    assert len(storage) == 1
    assert 0 == await f()
    assert len(storage) == 1

    await f.delete()
    assert storage == {}

    assert None is await f.get()

    f_value = 2
    await f.update()
    assert 2 == await f()

    storage["f"] = storage["f"][0], 1
    assert 1 == await f.get()
    assert 1 == await f()
    del storage["f"]
    f_value = 3
    assert 2 == await f.get()
    assert 3 == await f()
    assert 3 == await f.get()


def test_coder_func():
    storage = {}

    @ring.dict(storage)
    def f(a):
        return a

    encoded_value = f.encode("value")
    decoded_value = f.decode(encoded_value)
    assert encoded_value == decoded_value

    assert f("10") == "10"
    raw_value = storage.get(f.key("10"))  # raw value
    value = f.decode(raw_value)
    assert f.get("10") == value


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
            return "User{self.user_id}".format(self=self)

        @ring.dict(storage)
        def data(self):
            return self._data.copy()

    u1 = User(user_id=42, name="User 1")
    u1.data()

    encoded_value = u1.data.encode(u1.data.key())
    decoded_value = u1.data.decode(encoded_value)
    assert encoded_value == decoded_value

    raw_value = storage.get(u1.data.key())
    value = u1.data.decode(raw_value)
    assert u1.data.get() == value
