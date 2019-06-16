
import ring


def test_dict_gc_persistence_1():
    import time
    cache = {}

    @ring.dict(cache, maxsize=1)
    def f_persistent_1(i):
        return i

    for i in range(100):
        f_persistent_1(i)
        time.sleep(0.02)
        assert len(cache) <= 1

def test_dict_gc_persistence_default():
    import time
    cache = {}

    @ring.dict(cache)
    def f_persistent_default(i):
        return i

    for i in range(1000):
        f_persistent_default(i)
    time.sleep(0.1)
    assert len(cache) <= 128

def test_dict_gc_persistent_random_delete():
    import time
    cache = {}
    MAX_SIZE = 10

    @ring.dict(cache, maxsize=MAX_SIZE)
    def f_persistent_random_delete(i):
        return i

    for i in range(1000):
        f_persistent_random_delete(i)
        if i % 17 == 0:
            for pop_count in range(8):
                try:
                    cache.popitem()
                except KeyError:
                    pass
    time.sleep(0.1)
    assert len(cache) <= MAX_SIZE

def test_dict_gc_expire_1():
    import time
    cache = {}
    MAX_SIZE = 1

    @ring.dict(cache, maxsize=MAX_SIZE, expire=1)
    def f_expire_1(i):
        return i

    for i in range(MAX_SIZE * 100):
        f_expire_1(i)
        time.sleep(0.02)
        assert len(cache) <= MAX_SIZE

def test_dict_gc_expire_many():
    import time
    cache = {}
    MAX_SIZE = 50000

    @ring.dict(cache, maxsize=MAX_SIZE, expire=1)
    def f_expire_1(i):
        return i

    for i in range(MAX_SIZE * 10):
        f_expire_1(i)

    time.sleep(0.1)
    assert len(cache) <= MAX_SIZE

def test_dict_gc_expire_some():
    import time
    cache = {}

    @ring.dict(cache, maxsize=150, expire=1)
    def f_expire_some_expire(i):
        return i

    for i in range(100):
        f_expire_some_expire(i)
    time.sleep(1)
    for i in range(100, 200):
        f_expire_some_expire(i)
    assert len(cache) <= 150

def test_dict_gc_expire_default():
    import time
    cache = {}

    @ring.dict(cache, expire=1)
    def f_expire_default(i):
        return i

    for i in range(1000):
        f_expire_default(i)
    time.sleep(0.1)
    assert len(cache) <= 128

def test_dict_gc_expire_random():
    import time
    cache = {}

    @ring.dict(cache, maxsize=10, expire=1)
    def f_expire_random(i):
        return i

    for i in range(1000):
        f_expire_random(i)
    time.sleep(1)
    for i in range(1000, 2000):
        f_expire_random(i)
        if i % 17 == 0:
            for pop_count in range(8):
                try:
                    cache.popitem()
                except KeyError:
                    pass
    assert len(cache) <= 10
