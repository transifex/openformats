from __future__ import absolute_import

import io
import re
import unicodedata

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

    # The ? at the end of the string regex, makes it non-greedy in order to
    # allow trailing spaces to be preserved
    CONTENT_REGEX = re.compile(r'(<Content>\s*)(.*?)(\s*</Content>)')
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
        parser = etree.XMLParser(resolve_entities=False)
        designmap_tree = etree.fromstring(designmap, parser=parser)

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
        stripped_string = self.SPECIAL_CHARACTERS_REGEX.sub('', string).strip()
        if not stripped_string:
            return True
        try:
            float(string.strip())
            return True
        except ValueError:
            pass
        if not self._contains_translatable_character(stripped_string):
            return True
        return False

    def _contains_translatable_character(self, string):
        """
        Checks if a string contains at least one character that can be
        translated. We assume that translatable characters are the letters,
        the symbols and the punctuation.
        """
        acceptable = ["L", "P", "S"]

        for letter in string:
            char_type = unicodedata.category(letter)
            if char_type[0] in acceptable:
                return True
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
        opening_tag, string, closing_tag = match.groups()
        string = string.decode('utf-8')

        if self._can_skip_content(string):
            return match.group()
        order = next(self.order)
        string_object = OpenString(str(order), string, order=order)
        self.stringset.append(string_object)
        return "".join((opening_tag, string_object.template_replacement,
                        closing_tag))

    """ Compile Methods """

    def compile(self, template, stringset, **kwargs):
        # The content is a binary IDML file
        idml = UCF(io.BytesIO(template))

        self.stringset = list(stringset)

        # Iterate over the contents of the IDML file
        for key in self._get_ordered_stories(idml):
            try:
                story_content = idml[key]
            except KeyError:
                continue

            story_content = idml[key]
            idml[key] = self._compile_story(story_content)

        out = io.BytesIO()
        idml.save(out)
        return out.getvalue()

    def _compile_story(self, story_content):
        """ Handles the compilation of a single story
        args:
            story_content: the xml content of the story
        returns:
            compiled_story: the compiled story content
        """
        transcriber = Transcriber(story_content)
        hash_regex = re.compile('[a-z,0-9]{32}_tr')
        found = True
        while found:
            try:
                current_string = self.stringset.pop(0)
                hash_position = story_content.index(
                    current_string.template_replacement
                )
            except ValueError:
                found = False
                self.stringset.insert(0, current_string)
            except IndexError:
                break
            else:
                transcriber.copy_until(hash_position)
                transcriber.add(current_string.string.encode('utf-8'))
                transcriber.skip(len(current_string.template_replacement))

        # Update the XML file to contain the template strings
        transcriber.copy_until(len(story_content))
        compiled_story = transcriber.get_destination()
        # in case there are any hashes that have not been replaced, replace
        # them with an empty string
        compiled_story = hash_regex.sub('', compiled_story)
        return compiled_story
