import re

from ..handler import Handler, Transcriber, ParseError, String
from ..utils.compilers import OrderedCompilerMixin


class SrtHandler(OrderedCompilerMixin, Handler):
    name = "SRT"
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
        if not isinstance(content, unicode):
            content = content.decode("utf-8")
        transcriber = Transcriber(content)

        content = content.replace('\r\n', '\n')
        stringset = []
        for start, subtitle_section in self._generate_split_subtitles(content):
            transcriber.copy_until(start)
            offset, string = self._parse_section(start, subtitle_section)

            if string:
                stringset.append(string)

                transcriber.copy_until(offset)
                transcriber.add(string.template_replacement)
                transcriber.skip(len(string.string))
            else:
                transcriber.copy_until(start + len(subtitle_section))

        transcriber.copy_until(len(content))

        template = transcriber.get_destination()
        return template, stringset

    def _parse_section(self, offset, section):
        try:
            splitted = section.split('\n', 2)
            order, timings = splitted[:2]
            try:
                subtitle = splitted[2]
            except IndexError:
                # logger.warning(
                #     'Could not parse "{}...". Skipping... Error: '
                #     '{}'.format(section[:50], unicode(e)),
                #     exc_info=True
                # )
                return None, None
        except ValueError:
            raise ParseError(u'Could not parse subtitle section: "{}..."'.
                             format(section[:50]))

        try:
            int(order)
        except ValueError:
            raise ParseError(
                u'First line of subtitle section not a number: "{}..."'.
                format(section[:50])
            )

        # 2nd line, timings and maybe position
        try:
            split_timings = timings.split(None, 3)
            if split_timings[1] != "-->":
                raise ParseError("Invalid timings separator: {}".
                                 format(timings))
        except Exception:
            raise ParseError(
                'Second line of subtitle section does not propertly '
                'represent timing: "{}.\.."'.format(section[:50])
            )
        start, end = split_timings[0], split_timings[2]

        # Actual subtitle
        source, translation = order, subtitle
        string = String(
            source, translation, order=int(order),
            occurrences="{},{}".format(self._format_timing(start),
                                       self._format_timing(end)),
        )
        return offset + len(order) + 1 + len(timings) + 1, string

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
