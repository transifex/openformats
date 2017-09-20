def find_newline_type(content):
    try:
        first_newline_pos = content.index('\n')
    except ValueError:
        return 'UNIX'
    else:
        if first_newline_pos > 0 and content[first_newline_pos - 1] == '\r':
            return 'DOS'
        else:
            return 'UNIX'


def force_newline_type(content, newline_type):
    new_content = content.replace('\r\n', '\n')
    if newline_type == 'DOS':
        new_content = new_content.replace('\n', '\r\n')
    return new_content
