
import pytest


@pytest.mark.asyncio
async def test_async_func_method():
    import ring.func_asyncio
    cache = {}

    async def async_func(n):
        return n

    class A(object):
        @ring.func_asyncio.async_dict(cache)
        async def method(self, a, b):
            x = await async_func(100)
            return base + a * x + b

        @classmethod
        @ring.func_asyncio.async_dict(cache)
        async def cmethod(cls, a, b):
            x = await async_func(200)
            return base + a * x + b

    obj = A()

    base = 10000
    obj.method.delete(1, 2)
    assert (await obj.method(1, 2)) == 10102

    obj.cmethod.delete(1, 2)
    assert (await obj.cmethod(1, 2)) == 10202
