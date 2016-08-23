
from functools import wraps


class lazy_property(object):
    '''http://stackoverflow.com/questions/3012421/python-lazy-property-decorator
    '''

    def __init__(self, function):
        self.function = function

    def __get__(self, obj, cls):
        value = self.function(obj)
        setattr(obj, self.function.__name__, value)
        return value


class hybridmethod(object):
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, cls):
        context = obj if obj is not None else cls

        @wraps(self.func)
        def hybrid(*args, **kw):
            return self.func(context, *args, **kw)

        # optional, mimic methods some more
        hybrid.__func__ = hybrid.im_func = self.func
        hybrid.__self__ = hybrid.im_self = context

        return hybrid
