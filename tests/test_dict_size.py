
import ring


def test_dict_size_persistence_1():
    cache = {}
    MAX_SIZE = 1

    @ring.dict(cache, maxsize=MAX_SIZE)
    def f_persistent_1(i):
        return i

    for i in range(MAX_SIZE * 100):
        f_persistent_1(i)
        assert len(cache) <= 1
    assert len(cache) <= 1

def test_dict_size_persistence_default():
    cache = {}

    @ring.dict(cache)
    def f_persistent_default(i):
        return i

    for i in range(1000):
        f_persistent_default(i)
        assert len(cache) <= 128
    assert len(cache) <= 128

def test_dict_size_persistence_1000():
    cache = {}
    MAX_SIZE = 1000

    @ring.dict(cache, maxsize=MAX_SIZE)
    def f_persistent_default(i):
        return i

    for i in range(MAX_SIZE * 100):
        f_persistent_default(i)
        assert len(cache) <= MAX_SIZE
    assert len(cache) <= MAX_SIZE

def test_dict_size_persistent_with_delete():
    cache = {}
    MAX_SIZE = 10

    @ring.dict(cache, maxsize=MAX_SIZE)
    def f_persistent_with_delete(i):
        return i

    for i in range(MAX_SIZE * 100):
        f_persistent_with_delete(i)
        assert len(cache) <= MAX_SIZE
        if i % 17 == 0:
            for pop_count in range(8):
                if len(cache) > 0:
                    cache.popitem()


    assert len(cache) <= MAX_SIZE

def test_dict_size_persistent_infinite():
    cache = {}
    MAX_SIZE = None

    @ring.dict(cache, maxsize=MAX_SIZE)
    def f_persistent_infinite(i):
        return i

    for i in range(10000):
        f_persistent_infinite(i)
        assert len(cache) <= 10000

    assert len(cache) == 10000

def test_dict_size_expire_1():
    cache = {}
    MAX_SIZE = 1

    @ring.dict(cache, maxsize=MAX_SIZE, expire=1)
    def f_expire_1(i):
        return i

    for i in range(MAX_SIZE * 100):
        f_expire_1(i)
        assert len(cache) <= MAX_SIZE
    assert len(cache) <= MAX_SIZE

def test_dict_size_expire_default():
    cache = {}

    @ring.dict(cache, expire=1)
    def f_expire_default(i):
        return i

    for i in range(1000):
        f_expire_default(i)
        assert len(cache) <= 128
    assert len(cache) <= 128

def test_dict_size_expire_1000():
    cache = {}
    MAX_SIZE = 1000

    @ring.dict(cache, maxsize=MAX_SIZE, expire=1)
    def f_expire_1(i):
        return i

    for i in range(MAX_SIZE * 100):
        f_expire_1(i)
        assert len(cache) <= MAX_SIZE

    assert len(cache) <= MAX_SIZE

def test_dict_size_expire_some():
    import time
    cache = {}
    MAX_SIZE = 150

    @ring.dict(cache, maxsize=MAX_SIZE, expire=1)
    def f_expire_some_expire(i):
        return i

    for _ in range(5):
        for i in range(100):
            f_expire_some_expire(i)
            assert len(cache) <= MAX_SIZE
        time.sleep(1)
        for i in range(100, 200):
            f_expire_some_expire(i)
            assert len(cache) <= MAX_SIZE
        assert len(cache) <= MAX_SIZE


def test_dict_size_expire_with_delete():
    import time
    cache = {}

    @ring.dict(cache, expire=1)
    def f_expire_with_delete(i):
        return i

    for i in range(1000):
        f_expire_with_delete(i)
    time.sleep(1)
    for i in range(1000, 2000):
        f_expire_with_delete(i)
        assert len(cache) <= 128
        if i % 17 == 0:
            for pop_count in range(8):
                if len(cache) > 0:
                    cache.popitem()

    assert len(cache) <= 128

def test_dict_size_expire_infinite():
    cache = {}
    MAX_SIZE = None

    @ring.dict(cache, maxsize=MAX_SIZE)
    def f_expire_infinite(i):
        return i

    for i in range(10000):
        f_expire_infinite(i)
        assert len(cache) <= 10000

    assert len(cache) == 10000
