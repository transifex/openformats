from hashlib import md5


class OpenString(object):
    DEFAULTS = {
        'context': "",
        'order': None,
        'character_limit': None,
        'occurrences': None,
        'developer_comment': "",
        'flags': "",
        'fuzzy': None,
        'obsolete': None,
    }

    def __init__(self, key, string_or_strings, **kwargs):
        self.key = key
        if isinstance(string_or_strings, dict):
            self.pluralized = len(string_or_strings) > 1
            self._strings = {key: value
                             for key, value in string_or_strings.items()}
        else:
            self.pluralized = False
            self._strings = {5: string_or_strings}
        for key, value in self.DEFAULTS.items():
            setattr(self, key, kwargs.get(key, value))
        if 'pluralized' in kwargs:
            self.pluralized = kwargs['pluralized']

        self._template_replacement = None

    def __hash__(self):
        return hash((self.key, self.context, self.rule))

    def __repr__(self):
        return '"{}"'.format(self._strings[5].encode('utf-8'))

    @property
    def string(self):
        if self.pluralized:
            return self._strings
        else:
            return self._strings[5]

    def _get_template_replacement(self):
        if self.context:
            keys = [self.key] + self.context
        else:
            keys = [self.key, '']
        if self.pluralized:
            suffix = "pl"
        else:
            suffix = "tr"
        return "{hash}_{suffix}".format(
            hash=md5(':'.join(keys).encode('utf-8')).hexdigest(),
            suffix=suffix,
        )

    @property
    def template_replacement(self):
        if self._template_replacement is None:
            self._template_replacement = self._get_template_replacement()
        return self._template_replacement


class ParseError(Exception):
    pass


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


class Transcriber(object):
    """
    Create a template from an imported or compile an output file.

    This class will help with both creating a template from an imported
    file and with compiling a file from a template. It provides functions
    for copying text. It depends on 3 things, the source content
    (self.source), the target content (self.destination) which initially
    will contain an empty string and a pointer (self.ptr) which will
    indicate which parts of 'source' have already been copied to
    'destination' (and will be initialized to 0). The methods provided are
    demonstrated below::

        >>> transcriber = Transcriber(source)

        source:      <string name="foo">hello world</string>
        ptr:         ^ (0)
        destination: []

        >>> transcriber.copy_until(source.index('>') + 1)

        source:      <string name="foo">hello world</string>
        ptr:                            ^
        destination: ['<string name="foo">']

        >>> transcriber.add("aee8cc2abd5abd5a87cd784be_tr")

        source:      <string name="foo">hello world</string>
        ptr:                            ^
        destination: ['<string name="foo">', 'aee8cc2abd5abd5a87cd784be_tr']

        >>> transcriber.skip(len("hello world"))

        source:      <string name="foo">hello world</string>
        ptr:                                       ^
        destination: ['<string name="foo">', 'aee8cc2abd5abd5a87cd784be_tr']

        >>> transcriber.copy_until(source.index("</string>") +
        ...                        len("</string>"))

        source:      <string name="foo">hello world</string>
        ptr:                                                ^
        destination: ['<string name="foo">', 'aee8cc2abd5abd5a87cd784be_tr',
        '</string>']

        >>> print transcriber.get_destination()

        <string name="foo">aee8cc2abd5abd5a87cd784be_tr</string>
    """
    class SectionStart:
        pass

    class SectionEnd:
        pass

    def __init__(self, source):
        self.source = source
        self.destination = []
        self.ptr = 0

    def copy_until(self, end):
        self.destination.append(self.source[self.ptr:end])
        self.ptr = end

    def add(self, text):
        self.destination.append(text)

    def skip(self, offset):
        self.ptr += offset

    def skip_until(self, end):
        self.ptr = end

    def mark_section_start(self):
        self.destination.append(self.SectionStart)

    def mark_section_end(self):
        self.destination.append(self.SectionEnd)

    def remove_section(self, place=0):
        section_start_position = self._find_last_section_start(place)
        try:
            section_end_position = self.destination.index(
                self.SectionEnd, section_start_position
            )
        except ValueError:
            section_end_position = len(self.destination)
        for i in range(section_start_position, section_end_position + 1):
            self.destination[i] = None

    def _find_last_section_start(self, place=0):
        count = place
        for i, segment in enumerate(self.destination[::-1], start=1):
            if segment == self.SectionStart:
                if count == 0:
                    return len(self.destination) - i
                else:
                    count -= 1

    def get_destination(self):
        return "".join([entry
                        for entry in self.destination
                        if entry not in (self.SectionStart, self.SectionEnd,
                                         None)])
