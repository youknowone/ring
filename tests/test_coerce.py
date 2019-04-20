import sys

import pytest

from ring.func.base import coerce

try:
    from dataclasses import dataclass  # noqa
except ImportError:  # pragma: no cover
    pass


class RingKey(object):
    def __ring_key__(self):
        return 'ring key'


ring_key_instance = RingKey()
test_parameters = [
    ('test', 'test'),
    (1, 1),
    (ring_key_instance, 'ring key'),
]

if sys.version_info >= (3, 7):
    @dataclass
    class DataClass:
        name: str
        my_int: int
        my_dict: dict


    data = DataClass('name', 1, {'test': 1})
    test_parameters.append((data, "my_dict,{'test': 1},my_int,1,name,name"))


@pytest.mark.parametrize('value,result', test_parameters)
def test_coerce(value, result):
    assert coerce(value) == result
