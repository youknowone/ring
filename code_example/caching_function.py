import ring
import requests
import timeit
import time

@ring.func.dict({})
def get_url(url):
    """very slow function
    """
    time.sleep(3)
    return requests.get(url).content

timer_non_cached = timeit.Timer("get_url('http://www.naver.com')", globals=globals())
t_non_cached = timer_non_cached.timeit(1)
print(f"Non-Cached: {t_non_cached:.06f} seconds")

timer_cached = timeit.Timer("get_url('http://www.naver.com')", globals=globals())
t_cached = timer_cached.timeit(1)
print(f"Cached: {t_cached:.06f} seconds")
