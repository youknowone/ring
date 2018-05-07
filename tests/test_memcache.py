# coding: utf-8
import ring
import pymemcache.client
import memcache
import redis

import pytest


pymemcache_client = pymemcache.client.Client(('127.0.0.1', 11211))
memcache_client = memcache.Client(["127.0.0.1:11211"])
redis_client = redis.StrictRedis()

try:
    import pylibmc
except ImportError:
    pylibmc_client = None
else:
    pylibmc_client = pylibmc.Client(['127.0.0.1'])


@pytest.mark.parametrize('client', [
    memcache_client,
    pymemcache_client,
    pylibmc_client,
])
def test_memcache_key(client):
    if client is None:
        pytest.skip()

    @ring.memcache(client, 'ring-test')
    def f(a, b):
        r = a + b
        if isinstance(r, str):
            r = r.encode('utf-8')
        return r

    assert f.key('a', 'b') == 'ring-test:a:b'
    assert f.key('a', 'b with space') != 'ring-test:a:b with space'
    assert f.key('a', 'b with 문자') != 'ring-test:a:b with 문자'

    f.delete(1, 2)
    assert None is f.get(1, 2)
    assert 3 == int(f(1, b=2))
    assert 3 == int(f.get(1, 2))

    f.delete('a', 'b with space')
    assert None is f.get('a', 'b with space')
    assert b'ab with space' == f('a', b='b with space')
    assert b'ab with space' == f.get('a', b='b with space')
