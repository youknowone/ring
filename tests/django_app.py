"""Django sample app to test ring features.

To run as a stand-alone app, run:

.. code-block:: sh

    django-admin runserver --pythonpath=. --settings=django_app

"""
import random
import string
import datetime
import ring
import django
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.views.decorators.cache import cache_page
from django.shortcuts import redirect
if django.VERSION >= (2,):
    from django.urls import re_path
else:
    from django.conf.urls import url as re_path


SECRET_KEY = ''.join(
    random.choice(string.ascii_lowercase + string.digits) for _ in range(40))

SETTINGS = dict(
    DEBUG=False,
    SECRET_KEY=SECRET_KEY,
    ROOT_URLCONF=__name__,
    ALLOWED_HOSTS=['127.0.0.1', 'localhost', 'testserver'],
)

globals().update(SETTINGS)  # django-admin support
settings.configure(**SETTINGS)  # module import support


@cache_page(1)  # timeout=1
def django_page(request):
    content = str(datetime.datetime.now())
    return HttpResponse(content)


@ring.django.cache_page(1)  # timeout=1
def ring_page(request):
    content = str(datetime.datetime.now())
    return HttpResponse(content)


items = []


@ring.django.cache_page(60)
def chain_list(request):
    data = {
        'now': str(datetime.datetime.now()),
        'items': items,
    }
    return JsonResponse(data)


def chain_clear(request):
    del items[:]
    return redirect('chain_list')


def chain_post(request):
    delete_method = request.POST.get('delete', 0)
    value = request.POST.get('value', 0)
    items.append(value)
    if delete_method == 'reverse':
        chain_list.delete((request, 'chain_list'))
    elif delete_method == 'path':
        chain_list.delete((request, '/chain/list'))
    else:
        chain_list.delete(request)
        assert False
    return redirect('chain_list')


urlpatterns = [
    re_path(r'^django$', django_page),
    re_path(r'^ring$', ring_page),
    re_path(r'^ring/get$', ring_page.get),
    re_path(r'^ring/update$', ring_page.update),
    re_path(r'^ring/get_or_update$', ring_page.get_or_update),
    re_path(r'^chain/list$', chain_list, name='chain_list'),
    re_path(r'^chain/new$', chain_post),
    re_path(r'^chain/clear$', chain_clear),
]
