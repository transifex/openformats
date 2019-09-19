from __future__ import absolute_import

import io
import zipfile
from itertools import count

import six

from lxml import etree
from openformats.handlers import Handler
from openformats.strings import OpenString
from openformats.transcribers import Transcriber
from openformats.utils.xml import NewDumbXml as DumbXml


class InDesignHandler(Handler):
    name = "InDesign"
    extension = "idml"
    SPECIFIER = None
    PROCESSES_BINARY = True
    EXTRACTS_RAW = False

    def parse(self, content, **kwargs):
        order_gen, stringset, template_dict = count(), [], {}
        f_in = io.BytesIO(content)
        z_in = zipfile.ZipFile(f_in)
        filenames = self._get_story_filenames(z_in)

        for filename in filenames:
            story = z_in.read(filename).decode('utf-8')
            transcriber = Transcriber(story)
            story = transcriber.source
            root = DumbXml(story, story.index('<idPkg:Story'))
            for content in root.find_descendants('Content'):
                if content.content is None or not content.content.strip():
                    continue
                order = next(order_gen)
                string = OpenString(six.text_type(order), content.content,
                                    order=order)
                transcriber.copy_until(content.text_position)
                transcriber.add(string.template_replacement)
                transcriber.skip(len(content.content))
                stringset.append(string)
            transcriber.copy_to_end()
            template_dict[filename] = transcriber.get_destination()

        f_out = io.BytesIO()
        z_out = zipfile.ZipFile(f_out, 'w')
        for filename in z_in.namelist():
            z_out.writestr(z_in.getinfo(filename),
                           template_dict.get(filename, z_in.read(filename)))
        f_out.seek(0)
        return f_out.read(), stringset

    def compile(self, template, stringset, **kwargs):
        stringset, compiled_dict = iter(stringset), {}
        string = next(stringset)
        f_in = io.BytesIO(template)
        z_in = zipfile.ZipFile(f_in)
        filenames = self._get_story_filenames(z_in)
        for filename in filenames:
            template = z_in.read(filename).decode('utf8')
            transcriber = Transcriber(template)
            template = transcriber.source
            root = DumbXml(template, template.index('<idPkg:Story'))
            for content in root.find_descendants('Content'):
                if content.content != string.template_replacement:
                    continue
                transcriber.copy_until(content.text_position)
                transcriber.add(string.string)
                transcriber.skip(len(content.content))
                string = next(string, None)
            transcriber.copy_to_end()
            compiled_dict[filename] = transcriber.get_destination()

        f_out = io.BytesIO()
        z_out = zipfile.ZipFile(f_out, 'w')
        for filename in z_in.namelist():
            info = z_in.getinfo(filename)
            if filename in compiled_dict:
                z_out.writestr(info, compiled_dict[filename].encode('utf8'))
            else:
                z_out.writestr(info, z_in.read(filename))
        f_out.seek(0)
        return f_out.read()

    @staticmethod
    def _get_story_filenames(z_in):
        designmap = etree.fromstring(
            z_in.read('designmap.xml'),
            parser=etree.XMLParser(resolve_entities=False),
        )
        story_keys = {'Stories/Story_{}.xml'.format(key)
                      for key in designmap.attrib.get('StoryList', "").split()}
        return sorted(story_keys & set(z_in.namelist()))
