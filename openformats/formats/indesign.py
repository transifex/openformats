from __future__ import absolute_import

import io

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

    """ Parse Methods """

    def parse(self, content, **kwargs):
        stringset = []
        order = 0

        idml = UCF(io.BytesIO(content))
        ordered_stories = self._get_ordered_stories(idml)

        # Iterate over the contents of the IDML file
        for key in ordered_stories:
            try:
                story_content = idml[key]
            except KeyError:
                continue
            soup = BeautifulSoup(story_content, "xml")
            replacements = []
            # First, we save the strings to the string-set. We don't alter the
            # XML DOM contents because is will cause the for loops to process
            # the newly altered content too
            for content in self._get_all_contents(soup):
                for string in content.stripped_strings:
                    string_object = OpenString(string, string, order=order)
                    stringset.append(string_object)
                    replacements.append(string_object.template_replacement)
                    order += 1

            # Reiterate over the XML and replace the original strings with
            # their template replacements
            for content in self._get_all_contents(soup):
                for string in list(content.stripped_strings):
                    replacement = replacements.pop(0)
                    content.string = content.string.replace(string,
                                                            replacement, 1)

            # Update the XML file to contain the template strings
            idml[key] = str(soup)

        out = io.BytesIO()
        idml.save(out)
        template = out.getvalue()

        return template, stringset

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

    def _get_all_contents(self, idml):
        """Return an array with all the strings of an IDML file."""
        for story in idml.find_all("idPkg:Story"):
            for content in story.find_all("Content"):
                yield content

    """ Compile Methods """

    def compile(self, template, stringset, **kwargs):
        # The content is a binary IDML file
        idml = UCF(io.BytesIO(template))

        translations_dict = {s.template_replacement: s for s in stringset}

        # Iterate over the contents of the IDML file
        for key in idml.keys():
            if not key.startswith("Stories/"):
                continue
            soup = BeautifulSoup(idml[key], "xml")

            # Iterate over the story XML and replace the template hashes with
            # their translation string
            for content in self._get_all_contents(soup):
                strings = list(content.stripped_strings)
                for string_hash in strings:
                    translation = translations_dict.get(string_hash)
                    if content.string and translation:
                        content.string = content.string.replace(
                            string_hash, translation.string, 1
                        )

            # Update the XML file to contain the template strings
            idml[key] = str(soup)

        out = io.BytesIO()
        idml.save(out)

        return out.getvalue()
