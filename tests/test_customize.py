
import ring


def test_override_key():

    @ring.dict({})
    def f(v):
        return v

    @f.ring.key
    def f_key(v):
        return 'test:' + str(v)

    assert f.key(10) == 'test:10'

    @f.ring.encode
    def f_encode(v):
        return 'encoded', v

    @f.ring.decode
    def f_decode(v):
        assert v[0] == 'encoded'
        return v[1] + 1  # for test

    assert f.encode(10) == ('encoded', 10)
    assert f.decode(('encoded', 10)) == 11
    f.update(5)

    assert f.storage.backend['test:5'] == ('encoded', 5)
    assert f.get(5) == 6
