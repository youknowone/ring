
import ring


def test_basic_ignorable_key():
    @ring.func.dict({}, ignorable_keys=['ignorable'])
    def f(n, ignorable):
        return n + ignorable

    # the actual funtion can be different
    assert f.execute(10, 5) != f.execute(10, 10)
    # but key must be same
    assert f.key(10, 'ignorable') == f.key(10, 'must be not considered')

    # not ring-key compatible object
    class A(object):
        pass

    assert f.key(10, A())  # ignorable key must not affect key generation
