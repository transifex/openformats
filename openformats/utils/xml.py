import re


class DumbXml(object):
    """
        Describes and XML tag with its contents.

        The fact that the content starts with a '<' and ends with a '>' is
        assumed.

        You can iterate over the contents with the `find` method, which
        takes a tag name, a list of tag names or nothing as arguments and
        yields
    """

    OPENING_TAG_PAT = re.compile(
        r'^\s*\<(?P<name>[^\s\n\>]+)(?P<attrs>[^\>]*)\>',
        re.DOTALL
    )
    ATTR_PAT = re.compile(r'\b(?P<key>[^=]+)="(?P<value>[^"]+)"')
    COMMENT = "!--"
    SINGLE_TAG_PAT = re.compile(r'/\s*\>$')

    def __init__(self, content):
        """
            Does some parsing and sets the following attributes to `self`:

            * content: The content of the tag, including the opening/closing
                tags
            * name: The name of the tag
            * attrs: A dictionary of all the attributes of the tag with their
                values
            * inner_offset: the place of the character where the inner content
                of the tag starts, aka the length of the opening tag
            * inner: the inner content of the tag
        """

        self.content = content

        if self.content[:4] == "<!--":
            # Special case for comment
            self.inner_offset = 4
            self.name = self.COMMENT
            self.attrs = {}
            self.inner = self.content[4:self.content.index("-->")]
            return

        opening_match = self.OPENING_TAG_PAT.search(content)
        self.inner_offset = opening_match.end()
        self.name = opening_match.groupdict()['name']
        attrs = opening_match.groupdict()['attrs']
        self.attrs = {}
        for match in self.ATTR_PAT.finditer(attrs):
            self.attrs[match.groupdict()['key']] = match.groupdict()['value']

        closing_start, closing_end = self.find_closing(0)

        self.inner = self.content[opening_match.end():closing_start]

    def find(self, tags=[]):
        if isinstance(tags, (str, unicode)):
            tags = [tags]

        if not tags:
            pat = re.compile(r'\<', re.DOTALL)
        else:
            pat = re.compile(r'\<(?:{})'.format(
                '|'.join((re.escape(tag) for tag in tags))
            ), re.DOTALL)

        for match in pat.finditer(self.content):
            if match.start() == 0 or self._is_within_comment(match):
                continue
            closing_start, closing_end = self.find_closing(match.start())
            found = DumbXml(self.content[match.start():closing_end])
            if not tags or found.name in tags:
                offset = match.start()
                yield found, offset

    def find_closing(self, start):
        # assume start is on a '<'

        if self.content[start:start + 4] == "<!--":
            # Special case for comment
            closing_start = self.content[start:].index("-->")
            return start + closing_start, start + closing_start + 3

        opening_match = self.OPENING_TAG_PAT.search(self.content[start:])

        if self.SINGLE_TAG_PAT.search(opening_match.group()):
            # Single tag, eg `<foo a="b" />`
            return start + opening_match.end(), start + opening_match.end()

        tag_name = opening_match.groupdict()['name']
        tag_pat = re.compile(r'\<(?:(?:{tag_name})|(?:/{tag_name}\>))'.
                             format(tag_name=re.escape(tag_name)))
        match_generator = tag_pat.finditer(self.content[start:])
        first_match = match_generator.next()
        assert first_match and first_match.start() == 0 and\
            first_match.group()[1] != '/'
        count = 1
        for match in match_generator:
            matched = match.group()
            if matched[1] == '/' or matched == "-->":
                # closing tag
                count -= 1
            else:
                count += 1

            if count == 0:
                return start + match.start(), start + match.end()

    def _is_within_comment(self, match):
        # Previous opening comment
        try:
            opening = match.start() -\
                self.content[match.start()::-1].index("--!<")
        except ValueError:
            opening = None
        # Previous closing comment
        try:
            closing = match.start() -\
                self.content[match.start()::-1].index(">--")
        except ValueError:
            closing = None

        if opening is not None:
            if closing is not None:
                if closing > opening:
                    return False
                else:
                    return True
            else:
                return True
        else:
            return False


if __name__ == "__main__":
    document = DumbXml(
        '<resources><string name="foo">hello world</string></resources>'
    )
    strings = document.find('string')
    string, _ = strings.next()
    print "{}: {}".format(string.attrs['name'], string.inner)
