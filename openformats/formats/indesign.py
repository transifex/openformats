from __future__ import absolute_import

import io
import re

from itertools import count
from lxml import etree
from ucf import UCF

from openformats.handlers import Handler
from openformats.transcribers import Transcriber
from openformats.strings import OpenString


class InDesignHandler(Handler):
    """A handler class that parses and compiles .idml files that are created
    in Adobe's InDesign.

    IDML files contain multiple XML fragments that can be parsed to extract
    strings from.
    """

    name = "InDesign"
    extension = "idml"
    SPECIFIER = None
    PROCESSES_BINARY = True

    CONTENT_REGEX = re.compile(r'(<Content>)(.*)?(</Content>)')
    SPECIAL_CHARACTERS_REGEX = re.compile(r'<\?ACE \d+\?>|<Br/>;')

    """ Parse Methods """

    def __init__(self, *args, **kwargs):
        self.order = count()
        self.stringset = []
        super(InDesignHandler, self).__init__(*args, **kwargs)

    def parse(self, content, **kwargs):
        """ Parses .idml file content and returns the resource template and
            stringset.
            * Use UCF to unpack `content` to xml fragments
            * Parse all Story fragments to extract the translatable strings
              and replace them with a replacement hash
            * Pack the fragments back to create the template
            * Return the (template, stringset) tuple
        """

        idml = UCF(io.BytesIO(content))
        ordered_stories = self._get_ordered_stories(idml)

        # Iterate over the contents of the IDML file
        for key in ordered_stories:
            try:
                story_content = idml[key]
            except KeyError:
                continue
            story_content = self._find_and_replace(story_content)

            # Update the XML file to contain the template strings
            idml[key] = str(story_content)

        out = io.BytesIO()
        idml.save(out)
        template = out.getvalue()

        return template, self.stringset

    def _get_ordered_stories(self, idml):
        """
        Try to find the order the stories appear in the indesign document
        * Parse designmap.xml to get the StoryList attribute.
        * Return a list with the idml keys of the stories in the order they
          appear in StoryList
        """

        STORY_KEY = 'Stories/Story_{}.xml'
        BACKING_STORY = 'XML/BackingStory.xml'

        designmap = idml.get('designmap.xml')
        designmap_tree = etree.fromstring(designmap)

        story_ids = designmap_tree.attrib.get("StoryList", "").split()
        story_keys = [STORY_KEY.format(s) for s in story_ids]

        # In case there are stories that is not referenced in designmap.xml,
        # append them at the end of the list
        all_stories = {
            k for k in idml.keys()
            if k.startswith('Stories') or k == BACKING_STORY
        }
        story_keys.extend(all_stories - set(story_keys))
        return story_keys

    def _can_skip_content(self, string):
        """
        Checks if the contents of an XML files are translateable.
        Strings that contain only special characters or can be evaluated
        to a nunber are skipped.
        """
        if not self.SPECIAL_CHARACTERS_REGEX.sub('', string).strip():
            return True
        try:
            float(string.strip())
            return True
        except ValueError:
            pass
        return False

    def _find_and_replace(self, story_xml):
        """
        Finds all the translatable content in the given XML string
        replaces it with the string_hash and returns the resulting
        template while updating `self.stringset` in the process.
        args:
            story_xml (str): The xml content of a single Story of the IDML file
        returns:
            the input string with all translatable content replaced by the
            md5 hash of the string.
        """

        template = self.CONTENT_REGEX.sub(self._replace, story_xml)
        return template

    def _replace(self, match):
        """ Implements the logic used by `self.CONTENT_REGEX.sub(...)` to
        replace strings with their template replacement and appends new strings
        to `self.stringset`.
        """
        opening_tag = match.group(1)
        string = match.group(2).decode('utf-8')
        closing_tag = match.group(3)

        if self._can_skip_content(string):
            return opening_tag + string + closing_tag
        order = next(self.order)
        string_object = OpenString(str(order), string, order=order)
        self.stringset.append(string_object)
        return opening_tag + string_object.template_replacement + closing_tag

    """ Compile Methods """

    def compile(self, template, stringset, **kwargs):
        # The content is a binary IDML file
        idml = UCF(io.BytesIO(template))

        translations_dict = {s.template_replacement: s for s in stringset}
        hash_regex = re.compile('[a-z,0-9]{32}_tr')

        # Iterate over the contents of the IDML file
        for key in self._get_ordered_stories(idml):
            try:
                story_content = idml[key]
            except KeyError:
                continue

            for match in hash_regex.finditer(story_content):
                string_hash = match.group()
                story_content = story_content.replace(
                    string_hash,
                    translations_dict.get(string_hash).string.encode('utf-8')
                )

            # Update the XML file to contain the template strings
            idml[key] = story_content

        out = io.BytesIO()
        idml.save(out)

        return out.getvalue()
