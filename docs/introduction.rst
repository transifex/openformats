.. _introduction:


Why all this fuss?
##################

This library performs one of the most important functions of Transifex: The use
of language files to import and deliver translations.

How software localization works (in a nutshell)
===============================================

Your software stack comes with a tool (if it doesn't it should) that finds all
translatable text in your product and extracts it to a language file. We'll
call this the **source language file**, which is placed in a special folder in
your product's code.

Once you get that in place, your job is to produce several **target language
files**, once for each language you want your product to appear in and place
them in the same folder. These language files are very similar to the source
language file, all that changes is that in the same place your source strings
would be, there are now translations.

Your software stack will be able to pull translations from the language files
and put them in place of the original strings in your product, if the user
chooses a translated language. Tada!!!

Here is a sample source language file::

    # Translation file for Transifex.
    # Copyright (C) 2007-2010 Indifex Ltd.
    # This file is distributed under the same license as the Transifex package.
    msgid ""
    msgstr ""
    "Project-Id-Version: Transifex\n"
    "POT-Creation-Date: 2012-09-27 09:17+0000\n"
    "PO-Revision-Date: 2012-09-27 10:07+0000\n"
    "Last-Translator: Ilias-Dimitrios Vrachnis <vid@transifex.com>\n"
    "MIME-Version: 1.0\n"
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
    "Language: en\n"
    "Plural-Forms: nplurals=2; plural=(n != 1);\n"

    #: accounts/forms.py:22 accounts/forms.py:193
    msgid "Username"
    msgstr "Username"

    #: accounts/forms.py:24 accounts/forms.py:195
    msgid "Username must contain only letters, numbers, dots and underscores."
    msgstr "Username must contain only letters, numbers, dots and underscores."

    #: accounts/forms.py:27 accounts/forms.py:182 accounts/forms.py:198
    msgid "Email"
    msgstr "Email"

And here is a sample target language file::

    # Translation file for Transifex.
    # Copyright (C) 2007-2010 Indifex Ltd.
    # This file is distributed under the same license as the Transifex package.
    msgid ""
    msgstr ""
    "Project-Id-Version: Transifex\n"
    "POT-Creation-Date: 2012-09-27 09:17+0000\n"
    "PO-Revision-Date: 2015-05-26 21:35+0000\n"
    "Last-Translator: Kadministrator Bairaktaris <kb_admin@kbairak.com>\n"
    "MIME-Version: 1.0\n"
    "Content-Type: text/plain; charset=UTF-8\n"
    "Content-Transfer-Encoding: 8bit\n"
    "Language: el\n"
    "Plural-Forms: nplurals=2; plural=(n != 1);\n"

    #: accounts/forms.py:22 accounts/forms.py:193
    msgid "Username"
    msgstr "Όνομα χρήστη"

    #: accounts/forms.py:24 accounts/forms.py:195
    msgid "Username must contain only letters, numbers, dots and underscores."
    msgstr "Το όνομα χρήστη πρέπει να περιέχει μόνο γράμματα, αριθμούς, τελείες και κάτω παύλες."

    #: accounts/forms.py:27 accounts/forms.py:182 accounts/forms.py:198
    msgid "Email"
    msgstr "Διεύθυνση ηλεκτρονικού ταχυδρομείου"


File formats
============

As you can see, these language files have a peculiar format. These ones in
particular follow the PO file format, and are generated and parsed by an
open-source software called `gettext`_, which is popular in the open-source world.
The structure of these files allows compatible software to use their contents
to display the product in a variety of languages.

We need to support a variety of such file formats, as well of some formats that
weren't necessarily made for localization. For example, why shouldn't you be
able to use this process to localize subtitle files when the same process can
clearly work for those too?

.. _gettext: http://en.wikipedia.org/wiki/Gettext

Source::

    1
    00:01:45,105 --> 00:01:47,940
    Pinky: Gee, Brain, what do you want to do tonight?

    2
    00:02:45,105 --> 00:02:47,940
    Brain: The same thing we do every night, Pinky - try to take over the world!

Translated::

    1
    00:01:45,105 --> 00:01:47,940
    Pinky: Τι θες να κάνουμε απόψε Brain?

    2
    00:02:45,105 --> 00:02:47,940
    Brain: Ό,τι κάνουμε κάθε βράδυ, Pinky - θα προσπαθήσουμε να καταλάβουμε τον κόσμο!


How Transifex and Openformats deal with this task
=================================================

A **handler**, the basic unit of the Openformats library, will parse a
source language file and find the source strings in it. It will extract these
into a **stringset**, a collection of said content associated with some
metadata. This metadata's use is to:

    #.  Identify the strings and their translations inside the language files
    #.  Provide context for the translators

The source strings in the source file are replaced by **hashes**, constructed
by the metadata we just mentioned. The result of this process is what we call
the **template**.

Both the stringset and the template are stored in Transifex's database. The
translation editor will present the stringset to translators, abstracting the
template away, allowing them to focus solely on translation. Translators in
Transifex's web editor can work on a variety of files using the exact same
interface, not having to bother with the nature or the structure of the file
format being used.

Having saved the trasnlations in the database, the format handler can combine
those with the template to produce a target language file to be used in your
product. This process is called **compiling**. The handler searches for hashes
in the template, associates them with their relevant translation entries using
the metadata we stored during parsing and replaces the hashes with the
translations. The result is a target language file, ready to be used in your
product.


Step-by-step
============

Lets take the first subtitle from our previous example::

    1
    00:01:45,105 --> 00:01:47,940
    Pinky: Gee, Brain, what do you want to do tonight?

Here, we need to find the source string and something that will allow us to
identify its position later when we want to compile a language file. The string
is obviously "Pinky: Gee, Brain, what do you want to do tonight?". For our
metadata, we will use the ascending number on top, the '1', since we're
guaranteed that it is unique within the source file; if it isn't, our parser
should raise an error.

Hashing the identifier (the '1') will give us this:
'3afcdbfeb6ecfbdd0ba628696e3cc163_tr'. This is what we will replace our source
string with::

    1
    00:01:45,105 --> 00:01:47,940
    3afcdbfeb6ecfbdd0ba628696e3cc163_tr

This is the template!

In the web editor, the translators will produce a translated string based on
our source string:


.. table::

=========== =====================================================
 Language    Text
=========== =====================================================
  English    Pinky: Gee, Brain, what do you want to do tonight?
  Greek      Pinky: Τι θες να κάνουμε απόψε Brain?
=========== =====================================================

And, finally, the compiler will be able to find the hash in the template and
replace it with the translation::

    1
    00:01:45,105 --> 00:01:47,940
    Pinky: Τι θες να κάνουμε απόψε Brain?

