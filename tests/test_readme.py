def test_readme_function():
    import ring
    import memcache
    import requests

    mc = memcache.Client(["127.0.0.1:11211"])

    # working for mc, expire in 60sec
    @ring.memcache(mc, expire=60)
    def get_url(url):
        return requests.get(url).content

    # normal way - it is cached
    data = get_url("http://example.com")
    assert data
    # delete the cache
    get_url.delete("http://example.com")
    # get cached data or None
    data_or_none = get_url.get("http://example.com")
    assert data_or_none is None
    # force to update
    updated_data = get_url.update("http://example.com")
    assert updated_data == data

    # get internal cache key
    key = get_url.key("http://example.com")
    # and access directly to the backend
    direct_data = get_url.storage.get(key)
    assert data == direct_data


def test_readme_method():
    import ring
    import redis

    rc = redis.StrictRedis()

    class User(dict):
        def __ring_key__(self):
            return self["id"]

        # working for rc, no expiration
        # using json coder to cache and load
        @ring.redis(rc, coder="json")
        def data(self):
            return self.copy()

        # parameters are also ok!
        @ring.redis(rc, coder="json")
        def child(self, child_id):
            return {"user_id": self["id"], "child_id": child_id}

    user = User(id=42, name="Ring")

    # create and get cache
    user_data = user.data()  # cached
    user["name"] = "Ding"
    # still cached
    cached_data = user.data()
    assert user_data == cached_data
    # refresh
    updated_data = user.data.update()
    assert user_data != updated_data

    # id is the cache key so...
    user2 = User(id=42)
    # still hitting the same cache without `name`
    assert updated_data == user2.data()

    # cleanup
    user.data.delete()
