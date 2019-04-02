from __future__ import unicode_literals

import six


def find_newline_type(content):
    if isinstance(content, six.text_type):
        NEWLINE = "\n"
        CARRIAGE_RETURN = "\r"
    else:
        NEWLINE = b"\n"
        CARRIAGE_RETURN = b"\r"

    try:
        first_newline_pos = content.index(NEWLINE)
    except ValueError:
        return 'UNIX'
    else:
        if (first_newline_pos > 0 and
                content[first_newline_pos - 1] == CARRIAGE_RETURN):
            return 'DOS'
        else:
            return 'UNIX'


def force_newline_type(content, newline_type):
    if isinstance(content, six.text_type):
        NEWLINE = "\n"
        CARRIAGE_RETURN_NEWLINE = "\r\n"
    else:
        NEWLINE = b"\n"
        CARRIAGE_RETURN_NEWLINE = b"\r\n"

    new_content = content.replace(CARRIAGE_RETURN_NEWLINE, NEWLINE)
    if newline_type == 'DOS':
        new_content = new_content.replace(NEWLINE, CARRIAGE_RETURN_NEWLINE)
    return new_content
