
from django.conf import settings
from django.core.cache import caches
import ring

settings.configure(CACHES={
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
})


def test_django():

    @ring.django('default', expire=1)
    def f(a):
        return a * 100

    assert f.get(10) is None
    assert f(10) == 1000
    raw_key = f.key(10)
    assert caches['default'].get(raw_key) == f.get(10)

    @ring.django_default()
    def f(a):
        return a * 50

    assert f.get(10) == 1000
    caches['default'].delete(raw_key)
    assert f(10) == 500
