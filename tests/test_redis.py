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
    @ring.redis_hash(redis_client, 'test-hash-key', 'test-field')
    def f(a, b):
        r = a * 100 + b
        return str(r).encode('utf-8')

    # delete previous test
    f.delete(1, 2)
    f.delete(3, 4)
    f.delete(5, 6)
    f.delete(7, 8)

    assert f.key(1, 2) == 'test-field:1:2'

    f.delete(1, 2)
    assert False is f.has(1, 2)
    assert None is f.get(1, b=2)
    assert 102 == int(f(1, b=2))

    assert f.key(3, 4) == 'test-field:3:4'
    assert 102 == int(f.get(1, b=2))
    assert 304 == int(f(3, b=4))

    mv = f.get_many(
        (1, 2),
        (3, 4),
    )
    assert mv == [b'102', b'304']

    with pytest.raises(AttributeError):
        f.delete_many()
    f.delete(1, 2)
    f.delete(3, 4)

    mv = f.get_many(
        (1, 2),
        (3, 4),
    )
    assert mv == [None, None]

    mv = f.update_many(
        {'a': 5, 'b': 6},
        (7, 8),
    )
    assert mv == [b'506', b'708']

    mv = f.get_many(
        (1, 2),
        (3, 4),
        (5, 6),
        (7, 8),
    )
    assert mv == [None, None, b'506', b'708']
