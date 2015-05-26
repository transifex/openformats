

class Handler(object):

    def parse(self, content):
        # Parse input and return template and stringset
        raise NotImplemented()

    def compile(self, template, stringset):
        # uses template and stringset and returns the compiled file
        raise NotImplemented()
