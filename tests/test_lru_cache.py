import time
from functools import update_wrapper
from ring.func.lru_cache import LruCache, SENTINEL

try:
    from functools import _make_key
except ImportError:
    def _make_key(args, kwds, typed):
        return args, tuple(sorted(kwds.items()))


def test_lru_cache_porting():
    def lru_cache(maxsize=128, typed=False):
        if maxsize is not None and not isinstance(maxsize, int):
            raise TypeError('Expected maxsize to be an integer or None')

        def decorating_function(user_function):
            cache = LruCache(maxsize)

            def wrapper(*args, **kwds):
                # Size limited caching that tracks accesses by recency
                key = _make_key(args, kwds, typed)
                result = cache.get(key)
                if result is not SENTINEL:
                    return result
                result = user_function(*args, **kwds)
                cache.set(key, result)
                return result

            return update_wrapper(wrapper, user_function)

        return decorating_function

    global call_count
    call_count = 0

    @lru_cache(maxsize=128)
    def fibonacci(n):
        global call_count
        call_count += 1
        if n <= 1:
            return n
        return fibonacci(n - 1) + fibonacci(n - 2)

    assert fibonacci(10) == 55
    assert call_count == 11


def test_lru_object():
    lru = LruCache(3)

    lru.set('a', 10)
    lru.set('b', 20)
    lru.set('c', 30)
    assert 10 == lru.get('a')
    lru.set('d', 40)
    assert SENTINEL is lru.get('b')
    assert 30 == lru.get('c')

    lru.delete('c')
    assert 10 == lru.get('a')
    assert SENTINEL is lru.get('b')
    assert SENTINEL is lru.get('c')
    assert 40 == lru.get('d')

    lru.clear()
    for c in 'abcd':
        assert SENTINEL is lru.get(c)

    lru.cache_info()


def test_expire_object():
    lru = LruCache(3)

    lru.set('a', 10, expire=1)
    lru.set('b', 20, expire=2)
    lru.set('c', 30, expire=3)
    # Check if cache works well
    assert lru.get('a') == 10
    # Check if 'a' key expired
    time.sleep(1)
    assert lru.get('a') == SENTINEL
    # Check if lru logic works well
    lru.set('d', 40, expire=4)
    assert lru.get('b') == SENTINEL
    # Check if 'c' key not expired
    assert lru.get('c') == 30
