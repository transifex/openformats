# -*- coding: utf-8 -*-
from __future__ import absolute_import
"""
YAML representers
"""

import yaml


def unicode_representer(dumper, data):
    node = yaml.ScalarNode(tag=u'tag:yaml.org,2002:str', value=data)
    return node


def folded_unicode_representer(dumper, data):
    return dumper.represent_scalar(
        u'tag:yaml.org,2002:str', data, style='>')


def literal_unicode_representer(dumper, data):
    return dumper.represent_scalar(
        u'tag:yaml.org,2002:str', data, style='|')


def double_quoted_unicode_representer(dumper, data):
    return dumper.represent_scalar(
        u'tag:yaml.org,2002:str', data, style='"')


def single_quoted_unicode_representer(dumper, data):
    return dumper.represent_scalar(
        u'tag:yaml.org,2002:str', data, style="'")


def block_list_representer(dumper, data):
    return dumper.represent_sequence(
        'tag:yaml.org,2002:seq', data, flow_style=False)


def flow_list_representer(dumper, data):
    return dumper.represent_sequence(
        'tag:yaml.org,2002:seq', data, flow_style=True)


def ordered_dict_representer(dumper, data):
    return dumper.represent_dict(data.items())


def block_style_ordered_dict_representer(dumper, data):
    return dumper.represent_mapping(
        u'tag:yaml.org,2002:map', data.items(), flow_style=False)


def flow_style_ordered_dict_representer(dumper, data):
    return dumper.represent_mapping(
        u'tag:yaml.org,2002:map', data.items(), flow_style=True)
