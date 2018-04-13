# -*- coding: utf-8 -*-

"""
Wrapper classes to represent various styled objects
in a dictionary for generating YAML content
"""

from collections import OrderedDict


class folded_unicode(unicode):  # noqa: N801
    pass


class literal_unicode(unicode):  # noqa: N801
    pass


class double_quoted_unicode(unicode):  # noqa: N801
    pass


class single_quoted_unicode(unicode):  # noqa: N801
    pass


class BlockList(list):
    pass


class FlowList(list):
    pass


class BlockStyleOrderedDict(OrderedDict):
    pass


class FlowStyleOrderedDict(OrderedDict):
    pass
