import re

from ..handlers import Handler
from openformats.exceptions import ParseError
from openformats.strings import OpenString
from openformats.transcribers import Transcriber


class SrtHandler(Handler):
    name = "SRT"
    extension = "srt"

    NON_SPACE_PAT = re.compile(r'[^\s]')

    def _generate_split_subtitles(self, content):
        start = 0
        for section in content.split('\n\n'):
            # find first non-space character of section
            match = self.NON_SPACE_PAT.search(section)
            if match:
                yield start + match.start(), section.strip()
            start += len(section) + 2

    def parse(self, content):
        self.transcriber = Transcriber(content)
        source = self.transcriber.source
        stringset = []
        self.max_order = None
        for start, subtitle_section in self._generate_split_subtitles(source):
            self.transcriber.copy_until(start)
            offset, string = self._parse_section(start, subtitle_section)

            if string:
                stringset.append(string)

                self.transcriber.copy_until(offset)
                self.transcriber.add(string.template_replacement)
                self.transcriber.skip(len(string.string))
            else:
                self.transcriber.copy_until(start + len(subtitle_section))

        self.transcriber.copy_until(len(source))

        template = self.transcriber.get_destination()
        return template, stringset

    def _parse_section(self, offset, section):
        try:
            order_str, timings, string = section.split('\n', 2)
        except ValueError:
            raise ParseError(
                u"Not enough data on subtitle section on line {}. Order "
                u"number, timings and subtitle content are needed".
                format(self.transcriber.line_number)
            )

        # first line, order
        order_parse_error = False
        try:
            order_int = int(order_str.strip())
        except ValueError:
            order_parse_error = True
        else:
            if order_int <= 0:
                order_parse_error = True
        if order_parse_error:
            raise ParseError(
                u"Order number on line {line_no} ({order_no}) must be a "
                u"positive integer".format(
                    line_no=self.transcriber.line_number,
                    order_no=order_str,
                )
            )
        if self.max_order is not None and order_int <= self.max_order:
            raise ParseError(
                u"Order numbers must be in ascending order; number in line "
                u"{line_no} ({order_no}) is wrong".format(
                    line_no=self.transcriber.line_number,
                    order_no=order_int,
                )
            )
        else:
            self.max_order = order_int

        # second line, timings
        timings_parse_error = False
        try:
            splitted = timings.split(None, 3)
            if len(splitted) == 3:
                start, arrow, end = splitted
            else:
                start, arrow, end, _ = splitted
        except ValueError:
            timings_parse_error = True
        else:
            if arrow != u"-->":
                timings_parse_error = True
        if timings_parse_error:
            raise ParseError(
                u"Timings on line {} don't follow '[start] --> [end] "
                "(position)' pattern".format(
                    self.transcriber.line_number + 1
                )
            )
        try:
            start = self._format_timing(start)
        except ValueError:
            raise ParseError(
                u"Problem with start of timing at line {line_no}: '{start}'".
                format(line_no=self.transcriber.line_number + 1, start=start)
            )
        try:
            end = self._format_timing(end)
        except ValueError:
            raise ParseError(
                u"Problem with end of timing at line {line_no}: '{end}'".
                format(line_no=self.transcriber.line_number + 1, end=end)
            )

        # Content
        string_stripped = string.strip()
        if string_stripped == u"":
            raise ParseError(u"Subtitle is empty on line {}".
                             format(self.transcriber.line_number + 2))

        string = OpenString(order_str.strip(), string, order=order_int,
                            occurrences="{},{}".format(start, end))
        return offset + len(order_str) + 1 + len(timings) + 1, string

    def _format_timing(self, timing):
        try:
            rest, milliseconds = timing.split(',')
            milliseconds = "{:<03}".format(milliseconds)
        except ValueError:
            rest, milliseconds = timing, "000"
        hours, minutes, seconds = rest.split(':')
        hours, minutes, seconds, milliseconds = map(
            int,
            (hours, minutes, seconds, milliseconds)
        )
        return "{:02}:{:02}:{:02}.{:03}".format(hours, minutes, seconds,
                                                milliseconds)

    def compile(self, template, stringset):
        transcriber = Transcriber(template)
        template = transcriber.source
        stringset = iter(stringset)
        string = stringset.next()

        for start, subtitle_section in self.\
                _generate_split_subtitles(template):
            transcriber.copy_until(start)
            transcriber.mark_section_start()

            # Hash is supposed to follow second newline character
            first_newline = subtitle_section.index('\n')
            second_newline = subtitle_section.index('\n', first_newline + 1)
            hash_position = second_newline + 1

            if (subtitle_section[
                    hash_position:
                    hash_position + len(string.template_replacement)
                    ] == string.template_replacement):
                # found it
                transcriber.copy_until(start + hash_position)
                transcriber.add(string.string)
                transcriber.skip(len(string.template_replacement))
                transcriber.copy_until(start + len(subtitle_section))
                transcriber.mark_section_end()
                try:
                    string = stringset.next()
                except StopIteration:
                    pass
            else:
                # did not find it, must remove section
                transcriber.copy_until(start + len(subtitle_section))
                transcriber.mark_section_end()
                transcriber.remove_section()

        transcriber.copy_until(len(template))
        return transcriber.get_destination()
