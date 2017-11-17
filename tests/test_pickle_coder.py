
import ring
import ring.coder
import pymemcache.client
import memcache

import pytest
import datetime

def test_coder_pickle():
    assert b'I1\n.' == ring.coder.pickle.encode(1)
    assert 1 == ring.coder.pickle.decode(b'I1\n.')

    assert b"(dp0\nS'x'\np1\nI1\ns." == ring.coder.pickle.encode({'x': 1})
    assert {'x': 1} == ring.coder.pickle.decode(b"(dp0\nS'x'\np1\nI1\ns.")

client = memcache.Client(['127.0.0.1:11211'])

@ring.func.memcache(client, coder='pickle')
def now():
	return datetime.datetime.now()


def test_unexisting_coder():
    cache = {}

    with pytest.raises(TypeError):
        @ring.func.dict(cache, coder='messed-up')
        def f():
            pass


		
