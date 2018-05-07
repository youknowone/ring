
import pytest
import ring


@pytest.mark.asyncio
async def test_async_def_vanilla_function(storage_dict):
    storage = await storage_dict

    with pytest.raises(TypeError):
        @storage.ring(storage)
        def vanilla_function():
            pass


@pytest.mark.asyncio
async def test_async_def_func_method():
    cache = {}

    async def async_func(n):
        return n

    class A(object):
        def __str__(self):
            return 'A'

        @ring.aiodict(cache)
        async def method(self, a, b):
            x = await async_func(100)
            return base + a * x + b

        @ring.aiodict(cache)
        @classmethod
        async def cmethod(cls, a, b):
            x = await async_func(200)
            return base + a * x + b

    obj = A()

    base = 10000
    await obj.method.delete(1, 2)
    value = await obj.method(1, 2)
    assert value == 10102, value

    await obj.cmethod.delete(1, 2)
    value = await obj.cmethod(1, 2)
    assert value == 10202, value
