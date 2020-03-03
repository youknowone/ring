import ring
import requests
import timeit
import time
import redis

rc = redis.StrictRedis(host='192.168.0.156', port=6379, db=1, password=None)


@ring.redis(rc, coder='json', expire=30, dict_keys='data')
def get_url(obj):
    """very slow function
    """
    print('开始执行')
    time.sleep(1)
    return requests.get(obj['data']['url']).text


arg_data = {
    'taskid': 160,
    'data': {
        'url': 'https://www.tita.com'
    }
}
timer_non_cached = timeit.Timer("get_url({'taskid': 160,'data': {'url': 'https://www.tita.com'}})", globals=globals())
t_non_cached = timer_non_cached.timeit(100)
print("Non-Cached: {t_non_cached:.06f} seconds".format(t_non_cached=t_non_cached))

timer_cached = timeit.Timer("get_url({'taskid': 161,'data': {'url': 'https://www.tita.com'}})", globals=globals())
t_cached = timer_cached.timeit(100)
print("Cached: {t_cached:.06f} seconds".format(t_cached=t_cached))


@ring.redis(rc, coder='json', expire=30, dict_keys='data')
def get_url(url):
    """very slow function
    """
    print('开始执行')
    time.sleep(1)
    return requests.get(url).text


get_url('https://www.tita.com')
