import datetime
import functools
import json
import django
from django.core.cache import caches
from django.http import HttpResponse
from django.test.client import Client, RequestFactory
import ring

from . import django_app
import pytest

django.setup()


def test_django_cache():
    @ring.django.cache("default", expire=1)
    def f(a):
        return a * 100

    assert f.get(10) is None
    assert f(10) == 1000
    raw_key = f.key(10)
    assert caches["default"].get(raw_key) == f.get(10)

    @ring.django.cache()
    def f(a):
        return a * 50

    assert f.get(10) == 1000
    caches["default"].delete(raw_key)
    assert f(10) == 500
    f.delete(10)
    assert caches["default"].get(raw_key) is None


@pytest.mark.parametrize("view_func_source", [django_app.ring_page, None])
def test_django_cache_page(view_func_source):
    if view_func_source:
        view_func = view_func_source
    else:

        @ring.django.cache_page(1)
        def view_func(request):
            return HttpResponse(str(datetime.datetime.now()))

    request_factory = RequestFactory()
    request_main = functools.partial(request_factory.get, "/ring")

    view_func.delete((request_main(), None))
    response = view_func.get(request_main())
    assert response is None  # not cached

    response = view_func(request_main())  # execute and cache
    assert response
    executed_content = response.content

    response = view_func(request_main())
    assert executed_content == response.content  # cached

    response = view_func.get(request_main())
    assert response is not None  # still cached for get
    assert executed_content == response.content  # cached

    response = view_func.update(request_main())  # ignore cache
    assert executed_content != response.content  # new content
    print(response.content)
    executed_content = response.content

    response = view_func.update(request_main())  # ignore cache
    assert executed_content != response.content  # new content again
    print(response.content)
    executed_content = response.content

    response = view_func.get(request_main())
    assert response is not None
    print(response.content)
    assert executed_content == response.content  # cached

    with pytest.raises(NotImplementedError):
        view_func.touch(request_main())
    with pytest.raises(NotImplementedError):
        view_func.has(request_main())

    view_func.delete((request_main(), None))  # delete

    response = view_func.get(request_main())
    assert response is None  # no cache anymore


def test_django_cache_page_urls():
    client = Client()

    # get is not testable in this way
    with pytest.raises(ValueError):
        client.get("/ring/get")  # not cached

    # default behavior get_or_update
    response = client.get("/ring")  # execute and cache
    assert response
    executed_content = response.content

    response = client.get("/ring")
    assert response
    assert executed_content == response.content  # cached

    # update
    response = client.get("/ring/update")
    executed_content = response.content

    response = client.get("/ring/update")
    assert executed_content != response.content  # new content for update


def test_django_chaining():
    client = Client()

    client.get("/chain/clear")  # clear items
    response = client.get("/chain/list")
    cached_content = response.content
    assert json.loads(response.content.decode("utf-8"))["items"] == []

    response = client.get("/chain/list")
    assert cached_content == response.content  # ensure cache works

    response = client.post(
        "/chain/new", {"delete": "reverse", "value": "Reinhardt"}, follow=True
    )
    assert cached_content != response.content
    assert json.loads(response.content.decode("utf-8"))["items"] == ["Reinhardt"]

    response = client.post(
        "/chain/new", {"delete": "path", "value": "Django"}, follow=True
    )
    assert json.loads(response.content.decode("utf-8"))["items"] == [
        "Reinhardt",
        "Django",
    ]


def test_django_invalid_reverse():
    request_factory = RequestFactory()
    request = request_factory.get("/chain/new")

    # is silent failure acceptable?
    django_app.chain_list.delete((request, "fake-name"))
