import ring
from .test_func_sync import redis_client
import pytest

__all__ = ('redis_client', )


@pytest.mark.parametrize('expire', [
    1,
    None,
])
def test_redis(redis_client, expire):
    @ring.redis(redis_client, 'ring-test', expire=expire)
    def f(a, b):
        r = a * 100 + b
        return str(r).encode('utf-8')

    assert f.key(1, 2) == 'ring-test:1:2'

    f.delete(1, 2)
    assert False is f.has(1, 2)
    assert None is f.get(1, b=2)
    assert 102 == int(f(1, b=2))
    assert 102 == int(redis_client.get(f.key(1, 2)))
    assert True is f.has(1, 2)

    if expire is None:
        with pytest.raises(TypeError):
            f.touch(1, 2)
    else:
        f.touch(1, 2)

    @ring.redis(redis_client, 'ring-test', expire=expire, coder='json')
    def f(a, b):
        r = a * 100 + b
        return r

    mv = f.execute_many(
        {'a': 1, 'b': 2},
        (1, 4),
    )
    assert mv == [102, 104]

    with pytest.raises(AttributeError):
        f.delete_many()
    f.delete(1, 2)
    f.delete(1, 4)

    mv = f.get_many(
        (1, 2),
        {'a': 1, 'b': 4},
    )
    assert mv == [None, None]

    mv = f.update_many(
        {'a': 1, 'b': 2},
        (5, 1),
    )
    assert mv == [102, 501]

    mv = f.get_many(
        (1, 2),
        (1, 4),
        (5, 1),
    )
    assert mv == [102, None, 501]


def test_redis_hash(redis_client):
    @ring.redis_hash(redis_client, 'test-hash-key', 'test-field1')
    def f1(a, b):
        r = a * 100 + b
        return str(r).encode('utf-8')

    assert f1.key(1, 2) == 'test-field1:1:2'

    f1.delete(1, 2)
    assert False is f1.has(1, 2)
    assert None is f1.get(1, b=2)
    assert 102 == int(f1(1, b=2))

    @ring.redis_hash(redis_client, 'test-hash-key', 'test-field2')
    def f2(a, b):
        r = a * 200 + b
        return str(r).encode('utf-8')

    assert f2.key(1, 2) == 'test-field2:1:2'
    assert 202 == int(f2(1, b=2))
    assert 102 is int(f1.get(1, b=2))
