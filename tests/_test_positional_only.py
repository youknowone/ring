import ring


def test_positional_only():
    """issue gh #192"""

    class Klass1:
        def __str__(self):
            return "Klass1<>"

        @ring.lru()
        def test1(self, **kwargs):
            print(kwargs)

    class Klass2:
        def __str__(self):
            return "Klass2<>"

        @ring.lru()
        def test2(self, /, **kwargs):
            print(kwargs)

    Klass1().test1(a=2, b=3)
    Klass2().test2(a=2, b=3)
