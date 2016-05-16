from ..handlers import Handler
from ..utils.xml import NewDumbXml
from ..exceptions import ParseError


class XMLUtils(object):

    @staticmethod
    def raise_error(transcriber, tag, message, context=None):
        """Raises a ParseError with an appropriate message.

        :param transcriber: The transcriber that contains the template so far.
        :param tag: The xml tag where the error occured.
        :param message: The message to format and display with the error.
        :param context: Extra context to be used when formating the message.
        :raises: ParseError with the formated message param.
        """
        context = context or {}
        if 'line_number' not in context:
            transcriber.copy_until(tag.position)
            context['line_number'] = transcriber.line_number
        raise ParseError(message.format(**context))

    @staticmethod
    def should_compile(tag, openstring):
        """Checks if the current child should be compiled.

        :param tag: The tag to check if it should be compiled.
        :returns: True if the tag should be compiled else False.
        """
        return (
            openstring is not None and
            openstring.template_replacement ==
            tag.content.strip()
        )

    @staticmethod
    def validate_not_empty_string(transcriber, text, tag):
        """Validates that a string is not empty.

        :param transcriber: The transcriber that contains the template so far.
        :param text: The string to validate. Can be a basestring or a dict for
                        for pluralized strings.
        :param tag: The tag that the string is created from.Used to show the
                        appropriate line number in case an error occurs.
        :raises: Raises a ParseError if not all plurals of a pluralized string
                 are complete.
        :returns: True if the string is not empty else False.
        """
        # If dict then it's pluralized
        if isinstance(text, dict):
            if len(text) == 0:
                msg = u"No plurals found in <{tag}> tag on line {line_number}"
                XMLUtils.raise_error(
                    transcriber,
                    tag,
                    msg,
                    context={'tag': tag.tag}
                )

            # Find the plurals that have empty string
            text_value_set = set(
                value and value.strip() or "" for value in text.itervalues()
            )
            if "" in text_value_set and len(text_value_set) != 1:
                # If not all plurals have empty strings raise ParseError
                msg = (
                    u'Missing string(s) in <item> tag(s) in the <plural> tag '
                    u'on line {line_number}'
                )
                XMLUtils.raise_error(transcriber, tag, msg)
            elif "" in text_value_set:
                # All plurals are empty so skip `plurals` tag
                return False

            # Validate `other` rule is present
            if Handler._RULES_ATOI['other'] not in text.keys():
                msg = (
                    u"Quantity 'other' is missing from <plurals> tag "
                    u"on line {line_number}"
                )
                XMLUtils.raise_error(transcriber, tag, msg)
        elif not text or text.strip() == "":
            return False
        return True

    @staticmethod
    def validate_no_tail_characters(transcriber, tag):
        """Validates that the tag contains no extra tail characters.

        :param transcriber: The transcriber that contains the template so far.
        :param tag: The xml tag to be validated.
        :raises: ParseError if extra tail characters are found.
        """
        if tag.tail.strip() != "":
            # Check for tail characters
            transcriber.copy_until(tag.tail_position)
            msg = (u"Found trailing characters after <{tag}> tag on line "
                   u"{line_number}")
            tag = tag.tag
            if tag == NewDumbXml.COMMENT:
                tag = u"comment"
            XMLUtils.raise_error(
                tag,
                msg,
                context={'tag': tag,
                         'line_number': transcriber.line_number}
            )

    @staticmethod
    def validate_no_text_characters(transcriber, tag):
        """Validates that the tag contains no extra text characters.

        :param transcriber: The transcriber that contains the template so far.
        :param tag: The xml tag to be validated.
        :raises: ParseError if extra text characters are found.
        """
        if tag.text.strip() != "":
            # Check for text characters
            transcriber.copy_until(tag.text_position)
            msg = (u"Found leading characters inside <{tag}> tag on line "
                   u"{line_number}")
            XMLUtils.raise_error(
                tag, msg,
                context={'tag': tag.tag,
                         'line_number': transcriber.line_number}
            )
