try:
    from typing import Any, Optional, Tuple, List
except ImportError:
    class _Generic(object):
        def __getitem__(self, key):
            return _Generic()

    Optional = _Generic()
    Tuple = _Generic()
    List = _Generic()
    Any = None
