import sys

import pytest

from ring.func.base import coerce


class User(object):
    def __init__(self, user_id):
        self.user_id = user_id

    def __ring_key__(self):
        return 'User{self.user_id}'.format(self=self)

    def __str__(self):
        return str(self.user_id)


ring_key_instance = User(42)
test_parameters = [
    ('test', 'test'),
    (1, 1),
    (ring_key_instance, 'User42'),
    ([1, 2, 3, 4], '[1,2,3,4]'),
    (['1', '2', '3', '4'], "['1','2','3','4']"),
    ((1, 2, 3, 4), '(1,2,3,4)'),
    (('1', '2', '3', '4'), "('1','2','3','4')"),
]

if sys.version_info >= (3, 7):
    from tests._test_module_py37 import DataClass

    data = DataClass('name', 1, {'test': 1})
    test_parameters.append((data, "my_dict,{'test': 1},my_int,1,name,name"))


@pytest.mark.parametrize('value,result', test_parameters)
def test_coerce(value, result):
    assert coerce(value) == result
