
import pytest
from typing import Optional
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


@pytest.mark.parametrize('field,expected', [
    (None, {'a': int, 'b': str, 'return': float}),
    ('__call__', {'a': int, 'b': str, 'return': float}),
    ('execute', {'a': int, 'b': str, 'return': float}),
    ('get', {'a': int, 'b': str, 'return': Optional[float]}),
    ('get_or_update', {'a': int, 'b': str, 'return': float}),
    ('update', {'a': int, 'b': str, 'return': float}),
    ('key', {'a': int, 'b': str, 'return': str}),
    ('set', {'a': int, 'b': str, 'return': None}),
    ('delete', {'a': int, 'b': str, 'return': None}),
    ('touch', {'a': int, 'b': str, 'return': None}),

])
@pytest.mark.asyncio
async def test_annotation(field, expected):

    @ring.dict({})
    def f(a: int, b: str) -> float:
        pass

    @ring.aiodict({})
    async def g(a: int, b: str) -> float:
        pass

    if field is not None:
        owner = getattr(f, field)
    else:
        owner = f

    print('actual:', owner.__annotations__)
    print('expected:', expected)
    assert owner.__annotations__ == expected

    if field is not None:
        owner = getattr(g, field)
    else:
        owner = g

    print('actual:', owner.__annotations__)
    print('expected:', expected)
    assert owner.__annotations__ == expected
