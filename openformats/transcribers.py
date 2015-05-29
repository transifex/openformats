class Transcriber(object):
    """
    This class helps with creating a template from an imported file or compile
    an output file from a template.

    **Main functionality**

    This class will help with both creating a template from an imported file
    and with compiling a file from a template. It provides functions for
    copying text. It depends on 3 things, the source content (self.source), the
    target content (self.destination) which initially will contain an empty
    string and a pointer (self.ptr) which will indicate which parts of 'source'
    have already been copied to 'destination' (and will be initialized to 0).

    The main methods provided are demonstrated below::

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

        self.newline_count = 0

    def copy(self, offset):
        chunk = self.source[self.ptr:self.ptr + offset]
        self.destination.append(chunk)
        self.ptr += offset

        self.newline_count += chunk.count('\n')

    def copy_until(self, end):
        chunk = self.source[self.ptr:end]
        self.destination.append(chunk)
        self.ptr = end

        self.newline_count += chunk.count('\n')

    def add(self, text):
        self.destination.append(text)

    def skip(self, offset):
        chunk = self.source[self.ptr:self.ptr + offset]
        self.newline_count += chunk.count('\n')

        self.ptr += offset

    def skip_until(self, end):
        chunk = self.source[self.ptr:end]
        self.newline_count += chunk.count('\n')

        self.ptr = end

    def mark_section_start(self):
        self.destination.append(self.SectionStart)

    def mark_section_end(self):
        self.destination.append(self.SectionEnd)

    def remove_section(self, place=0):
        """
        You can mark sections in the target file and optionally remove them.
        Insert the section-start and section-end bookmarks wherever you want to
        mark a section. Then you can remove a section with `remove_section()`.
        For example::

            >>> transcriber = Transcriber(source)

            source:      <keep><remove>
            ptr:         ^ (0)
            destination: []

            >>> transcriber.mark_section_start()
            >>> transcriber.copy_until(1)  # copy until first '<'
            >>> string = source[1:source.index('>')]
            >>> transcriber.add("asdf")  # add the hash
            >>> transcriber.skip(len(string))
            >>> transcriber.copy_until(source.index('>') + 1)
            >>> transcriber.mark_section_end()

            source:      <keep><remove>
            ptr:               ^
            destination: [SectionStart, '<', 'asdf', '>', SectionEnd]

            >>> if string == "remove":
            ...     transcriber.remove_section()

            (nothing happens)

            >>> start = source.index('>') + 1

            >>> # Same deal as before, mostly
            >>> transcriber.mark_section_start()
            >>> transcriber.copy_until(start + 1)  # copy until second '<'
            >>> string = source[1:source.index('>', start)]
            >>> transcriber.add("fdsa")  # add the hash
            >>> transcriber.skip(len(string))
            >>> transcriber.copy_until(source.index('>', start) + 1)
            >>> transcriber.mark_section_end()

            source:      <keep><remove>
            ptr:                       ^
            destination: [SectionStart, '<', 'asdf', '>', SectionEnd,
                          SectionStart, '<', 'fdsa', '>', SectionEnd]

            >>> if string == "remove":
            ...     transcriber.remove_section()

            source:      <keep><remove>
            ptr:                       ^
            destination: [SectionStart,  '<', 'asdf', '>',  SectionEnd,
                          None        , None, None  , None, None      ]

            (The last section was replaced with Nones)

            Now, when you try to get the result with `get_destination()`, the
            Nones, SectionStarts and SectionEnds will be ommited:

            >>> transcriber.get_destination()

            <asdf>
        """
        section_start_position = self._find_last_section_start(place)
        try:
            section_end_position = self.destination.index(
                self.SectionEnd, section_start_position
            )
        except ValueError:
            section_end_position = len(self.destination) - 1
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

    @property
    def line_number(self):
        """
        The transcriber remembers how many newlines it has went over on the
        source, both when copying and skipping content. This allows you to
        pinpoint the line-number a parse-error has occured. For example::

            source:
                first line
                second line
                third line with error
                fourth line

            >>> transcriber = Transcriber(source)
            >>> for line in source.split("\ n"):
            >>>     if "error" not in line:
            >>>         # include the newline too
            >>>         transcriber.copy(len(line) + 1)
            >>>     else:
            >>>         raise ParseError(
            >>>             "Error on line {line_no}: '{line}'".format(
            >>>                 line_no=transcriber.line_number,
            >>>                 line=line
            >>>             )
            >>>         )

            This will raise a::

            >>> ParseError("Error on line 3: 'third line with error'")
        """
        return self.newline_count + 1

    def get_destination(self):
        return "".join([entry
                        for entry in self.destination
                        if entry not in (self.SectionStart, self.SectionEnd,
                                         None)])
