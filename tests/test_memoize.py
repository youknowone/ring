
import ring
import pytest


def test_fibonacci():
    cache = {}

    @ring.func.dict(cache, ignorable_keys=['use_cache'])
    def fibonacci(n, use_cache):
        if use_cache:
            raise RuntimeError('it is not cached!')
        if n <= 1:
            return n
        return fibonacci(n - 2, use_cache) + fibonacci(n - 1, use_cache)

    with pytest.raises(RuntimeError):
        fibonacci(9, use_cache=True)
    assert 55 == fibonacci(10, use_cache=False)
    assert 21 == fibonacci(8, use_cache=True)
