import abc
import sys

import pytest

try:
    import numpy
except ImportError:

    @pytest.mark.skip("`import numpy` failed")
    def test_numpy_skipped():
        pass

    numpy = None

from ring.func.base import coerce


class User(object):
    def __init__(self, user_id):
        self.user_id = user_id

    def __ring_key__(self):
        return "User{self.user_id}".format(self=self)

    def __str__(self):
        return str(self.user_id)


class HashUser(object):
    def __init__(self, user_id):
        self.user_id = user_id

    def __hash__(self):
        return hash("User{self.user_id}".format(self=self))

    def __str__(self):
        return str(self.user_id)


class ABCUser(abc.ABC):
    pass


ring_key_instance = User(42)
ring_hash_instance = HashUser(42)
test_parameters = [
    ("test", "test"),
    (1, 1),
    (ring_key_instance, "User42"),
    (ring_hash_instance, "HashUser:hash:{}".format(hash("User42"))),
    ([1, 2, 3, 4], "[1,2,3,4]"),
    (["1", "2", "3", "4"], "['1','2','3','4']"),
    ({1, 2, 3, 4}, "{1,2,3,4}"),
    ({"1", "2", "3", "4"}, "{'1','2','3','4'}"),
    (("1", "2", "3", "4"), "('1','2','3','4')"),
    (User, "User"),
    (ABCUser, "ABCUser"),
]
if numpy is not None:
    test_parameters.extend(
        [
            (numpy.array([1, 2, 3, 4]), "ndarray:[1,2,3,4]"),
            (numpy.array((1, 2, 3, 4)), "ndarray:[1,2,3,4]"),
            (numpy.array(["1", "2", "3", "4"]), "ndarray:['1','2','3','4']"),
            (numpy.array(("1", "2", "3", "4")), "ndarray:['1','2','3','4']"),
        ]
    )

if sys.version_info >= (3, 7):
    from tests._test_module_py37 import DataClass

    data = DataClass("name", 1, {"test": 1})
    test_parameters.append((data, "DataClassmy_dict,{'test': 1},my_int,1,name,name"))


@pytest.mark.parametrize("value,result", test_parameters)
def test_coerce(value, result):
    in_memory_storage = type(value).__hash__ != object.__hash__
    assert coerce(value, in_memory_storage) == result
