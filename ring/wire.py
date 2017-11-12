

class Wire(object):

    def __init__(self, preargs):
        assert isinstance(preargs, tuple)
        self.preargs = preargs

    def reargs(self, args):
        if self.preargs:
            args = self.preargs + args
        return args
