from string import ascii_letters, digits
from random import choice


def generate_random_string(length=20):
    return ''.join(choice(ascii_letters + digits) for _ in range(length))


def strip_leading_spaces(source):
    r"""
    This is to help you write multilingual strings as test inputs in your
    tests without screwing up your code's syntax. Eg::

        '''
            1
            00:01:28.797 --> 00:01:30.297 X:240 Y:480
            Hello world
        '''

    will be converted to::

        '\n1\n00:01:28.797 --> 00:01:30.297 X:240 Y:480\nHello world\n'
    """

    return '\n'.join((line.lstrip() for line in source.split('\n')))
