import ring
import requests
import timeit
import time


@ring.dict({})
def get_url(url):
    """very slow function"""
    time.sleep(1)
    return requests.get(url).content


timer_non_cached = timeit.Timer("get_url('http://www.naver.com')", globals=globals())
t_non_cached = timer_non_cached.timeit(1)
print("Non-Cached: {t_non_cached:.06f} seconds".format(t_non_cached=t_non_cached))


timer_cached = timeit.Timer("get_url('http://www.naver.com')", globals=globals())
t_cached = timer_cached.timeit(1)
print("Cached: {t_cached:.06f} seconds".format(t_cached=t_cached))
