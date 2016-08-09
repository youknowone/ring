

class lazy_property(object):
    '''http://stackoverflow.com/questions/3012421/python-lazy-property-decorator
    '''

    def __init__(self, function):
        self.function = function

    def __get__(self, obj, cls):
        value = self.function(obj)
        setattr(obj, self.function.__name__, value)
        return value
