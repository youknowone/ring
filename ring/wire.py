

class Wire(object):

    def __init__(self, preargs, anon_padding=False):
        assert isinstance(preargs, tuple)
        self.preargs = preargs
        self.anon_padding = anon_padding

    def reargs(self, args, padding):
        if self.preargs:
            args = self.preargs + args
        elif padding and self.anon_padding:
            args = (None,) + args
        return args
