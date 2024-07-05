import re
from itertools import count

from openformats.exceptions import ParseError
from openformats.strings import OpenString
from openformats.transcribers import Transcriber

from ..handlers import Handler


class VttHandler(Handler):
    name = "VTT"
    extension = "vtt"
    EXTRACTS_RAW = False

    NON_SPACE_PAT = re.compile(r"[^\s]")

    def _generate_split_subtitles(self, content, **kwargs):
        start = 0
        for section in content.split("\n\n"):  # sections are separated by blank lines
            # find first non-space character of section
            match = self.NON_SPACE_PAT.search(section)
            if match:
                yield start + match.start(), section.strip()
            start += len(section) + 2

    def parse(self, content, **kwargs):
        self.transcriber = Transcriber(content)
        source = self.transcriber.source
        stringset = []
        self._order = count()
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
        if not template.startswith("WEBVTT"):
            raise ParseError("VTT file should start with 'WEBVTT'!")
        return template, stringset

    def _parse_section(self, offset, section):
        src_strings = section.split("\n")  # identifier_str is optional in VTT

        timings = ""
        timings_index = -1
        for i in range(len(src_strings)):
            str = src_strings[i]
            if "-->" in str:
                timings = str
                timings_index = i
                break

        if timings_index < 0:
            return None, None

        # Identifier (lines preceding the line with timings) is optional in VTT.
        # Identifier can be either numberic or textual, and it is not necessarily unique.
        identifier = "\n".join(src_strings[:timings_index])

        # timings
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
            if arrow != "-->":
                timings_parse_error = True
        if timings_parse_error:
            raise ParseError(
                f"Timings on line {self.transcriber.line_number + 1} "
                "don't follow '[start] --> [end] (position)' pattern"
            )
        try:
            start = self._format_timing(start)
        except ValueError:
            raise ParseError(
                f"Problem with start of timing at line {self.transcriber.line_number + 1}: '{start}'"
            )
        try:
            end = self._format_timing(end)
        except ValueError:
            raise ParseError(
                f"Problem with end of timing at line {self.transcriber.line_number + 1}: '{end}'"
            )

        # Content
        string_to_translate = "\n".join(src_strings[timings_index + 1 :])
        if string_to_translate == "":
            # Do not include an empty subtitle in the stringset
            return None, None

        string = OpenString(
            timings,
            string_to_translate,
            occurrences=f"{start},{end}",
            order=next(self._order),
        )
        offset += len(identifier) + len(timings) + 1
        if len(identifier):
            offset += 1
        return offset, string

    def _format_timing(self, timing):
        try:
            rest, milliseconds = timing.split(".")
            milliseconds = f"{milliseconds:<03}"
        except ValueError:
            rest, milliseconds = timing, "000"
        # timing may or may not contain hours part
        if rest.count(":") == 1:
            minutes, seconds = rest.split(":")
            minutes, seconds, milliseconds = (
                int(minutes),
                int(seconds),
                int(milliseconds),
            )
            return f"{minutes:02}:{seconds:02}.{milliseconds:03}"
        elif rest.count(":") == 2:
            hours, minutes, seconds = rest.split(":")
            hours, minutes, seconds, milliseconds = (
                int(hours),
                int(minutes),
                int(seconds),
                int(milliseconds),
            )
            return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"
        else:
            raise ParseError(
                f"Unexpected timing format on line {self.transcriber.line_number + 2}"
            )

    def compile(self, template, stringset, **kwargs):
        transcriber = Transcriber(template)
        template = transcriber.source
        stringset = iter(stringset)
        try:
            string = next(stringset)
        except StopIteration:
            raise ParseError("stringset cannot be empty")

        for start, subtitle_section in self._generate_split_subtitles(template):
            transcriber.copy_until(start)
            transcriber.mark_section_start()

            # Find hash after timings
            hash_position = -1
            if subtitle_section.count("-->") > 0:
                arrow_pos = subtitle_section.index("-->")
                try:
                    end_of_timings = subtitle_section.index(
                        "\n", arrow_pos + len("-->")
                    )
                    hash_position = end_of_timings + 1
                except ValueError:
                    # No newlines after timing: subtitle is missing
                    pass

            if hash_position < 0:
                transcriber.copy_until(start + len(subtitle_section))
                transcriber.mark_section_end()
            elif (
                subtitle_section[
                    hash_position : hash_position + len(string.template_replacement)
                ]
                == string.template_replacement
            ):
                # found it
                transcriber.copy_until(start + hash_position)
                transcriber.add(string.string)
                transcriber.skip(len(string.template_replacement))
                transcriber.copy_until(start + len(subtitle_section))
                transcriber.mark_section_end()
                try:
                    string = next(stringset)
                except StopIteration:
                    pass
            else:
                # did not find it, must remove section
                transcriber.copy_until(start + len(subtitle_section))
                transcriber.mark_section_end()
                transcriber.remove_section()

        transcriber.copy_until(len(template))
        return transcriber.get_destination()
