# coding: utf-8

# Copyright (c) 2021 Blind Pandas Team
# This file is covered by the GNU General Public License.

import os
import json
import globalVars
from .helpers import import_bundled_library, DATA_DIRECTORY


with import_bundled_library():
    import enchant


# Constants
SPELLCHECK_DICTIONARIES_DIRECTORY = os.path.join(globalVars.appArgs.configPath, "spellcheck_dictionaries")
with open(os.path.join(DATA_DIRECTORY, "dictionary_download_urls.json"), "r") as file:
    LANGUAGE_DOWNLOAD_URLS = json.load(file)



class LanguageDictionaryNotAvailable(LookupError):
    """Raised when the given language has no dictionary."""

    def __init__(self, language):
        self.language = language


class LanguageDictionaryDownloadable(LanguageDictionaryNotAvailable):
    """Raised if the language dictionary is unavailable locally, but available for download."""

    def __init__(self, language, download_url, *args, **kwargs):
        super().__init__(language, *args, **kwargs)
        self.download_url = download_url


def set_enchant_language_dictionaries_directory():
    os.environ["ENCHANT_CONFIG_DIR"] = SPELLCHECK_DICTIONARIES_DIRECTORY


def ensure_language_dictionary_available(lang_tag):
    if lang_tag in enchant.list_languages():
        return True
    elif lang_tag in LANGUAGE_DOWNLOAD_URLS:
        raise LanguageDictionaryDownloadable(lang_tag, LANGUAGE_DOWNLOAD_URLS[lang_tag])
    elif "_" in lang_tag:
        return ensure_language_dictionary_available(lang_tag.split("_")[0])
    else:
        raise LanguageDictionaryNotAvailable(lang_tag)
