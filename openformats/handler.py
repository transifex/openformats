class Handler(object):
    RULES_ATOI = {'zero': 0, 'one': 1, 'two': 2, 'few': 3, 'many': 4,
                  'other': 5}
    RULES_ITOA = {0: "zero", 1: "one", 2: "two", 3: "few", 4: "many",
                  5: "other"}

    def parse(self, content):
        # Parse input and return template and stringset
        raise NotImplemented()

    def compile(self, template, stringset):
        # uses template and stringset and returns the compiled file
        raise NotImplemented()


