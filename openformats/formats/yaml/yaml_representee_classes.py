# -*- coding: utf-8 -*-

"""
Wrapper classes to represent various styled objects
in a dictionary for generating YAML content
"""

from collections import OrderedDict

from openformats.formats.yaml.constants import YAML_STRING_ID


class plain_unicode(unicode):  # noqa: N801

    def __new__(self, value, tag=None):
        self = super(plain_unicode, self).__new__(self, value)
        self.tag = tag or YAML_STRING_ID
        return self

    pass


class folded_unicode(plain_unicode):  # noqa: N801
    pass


class literal_unicode(plain_unicode):  # noqa: N801
    pass


class double_quoted_unicode(plain_unicode):  # noqa: N801
    pass


class single_quoted_unicode(plain_unicode):  # noqa: N801
    pass


class BlockList(list):
    pass


class FlowList(list):
    pass


class BlockStyleOrderedDict(OrderedDict):
    pass


class FlowStyleOrderedDict(OrderedDict):
    pass
