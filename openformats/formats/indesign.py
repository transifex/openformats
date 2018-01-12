from __future__ import absolute_import

import io
import re

from collections import OrderedDict
from itertools import chain
from bs4 import BeautifulSoup
from ucf import UCF

from ..handlers import Handler
from ..strings import OpenString


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

    def parse(self, content, **kwargs):
        """ Parses .idml file content and returns the resource template and
            stringset.
            * Use UCF to unpack `content` to xml fragments
            * Parse all Story fragments to extract the translatable strings
              and replace them with a replacement hash
            * Pack the fragments back to create the template
            * Return the (template, stringset) tuple
        """
        self.stringset = []
        self.order = 0

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
        * Parse designmap.xml to get the spreads in the orderthe appear in the
          document.
        * Parse each Spread in order to get all the TextFrame elemements in the
          order they appear
        * Get the ParentStory attribute of each TextFrame
        * Return a list with unique Story keys while maintaining the order in
          which they were found.
        """
        ordered_story_ids = []
        STORY_KEY = 'Stories/Story_{}.xml'
        designmap = idml.get('designmap.xml')
        designmap_soup = BeautifulSoup(designmap, 'xml')
        masterspreads = designmap_soup.find_all('idPkg:MasterSpread')
        spreads = designmap_soup.find_all('idPkg:Spread')

        for spread in chain(masterspreads, spreads):
            spread_key = spread.attrs.get('src')
            spread_xml = idml.get(spread_key)
            if not spread_xml:
                continue
            spread_content = BeautifulSoup(spread_xml, 'xml')
            text_frames = spread_content.find_all('TextFrame')
            ordered_story_ids.extend([
                frame.attrs.get('ParentStory') for frame in text_frames
            ])

        unique_story_ids = OrderedDict.fromkeys(ordered_story_ids)
        unique_stories = [STORY_KEY.format(s) for s in unique_story_ids]

        # In case there are stories that is not referenced by any TextFrame,
        # append them at the end of the list
        all_stories = {k for k in idml.keys() if k.startswith('Stories')}
        unique_stories.extend(all_stories - set(unique_stories))
        return unique_stories

    def _can_skip_content(self, string):
        """
        Checks if the contents of an XML files are translateable.
        Strings that contain only special characters or can be evaluated
        to a nunber are skipped.
        """
        if not self.SPECIAL_CHARACTERS_REGEX.sub('', string).strip():
            return True
        try:
            float(string)
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
        string_object = OpenString(string, string, order=self.order)
        self.stringset.append(string_object)
        self.order += 1
        return opening_tag + string_object.template_replacement + closing_tag

    """ Compile Methods """

    def compile(self, template, stringset, **kwargs):
        # The content is a binary IDML file
        idml = UCF(io.BytesIO(template))

        translations_dict = {s.template_replacement: s for s in stringset}
        hash_regex = re.compile('[a-z,0-9]{32}_tr')

        # Iterate over the contents of the IDML file
        for key in idml.keys():
            if not key.startswith("Stories/"):
                continue

            story_content = idml[key]
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
