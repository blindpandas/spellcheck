# coding: utf-8

# Copyright (c) 2021 Blind Pandas Team
# This file is covered by the GNU General Public License.

import os
import zipfile
import json
import globalVars
from io import BytesIO
from functools import partial
from .helpers import import_bundled_library, DATA_DIRECTORY


with import_bundled_library():
    import enchant
    import httpx
    from concurrent.futures import ThreadPoolExecutor


# Constants
THREAD_POOL_EXECUTOR = ThreadPoolExecutor()
SPELLCHECK_DICTIONARIES_DIRECTORY = os.path.join(globalVars.appArgs.configPath, "spellcheck_dictionaries")
DICTIONARY_FILE_EXTS = {".dic", ".aff",}
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
    if not os.path.isdir(SPELLCHECK_DICTIONARIES_DIRECTORY):
        os.mkdir(SPELLCHECK_DICTIONARIES_DIRECTORY)
    os.environ["ENCHANT_CONFIG_DIR"] = SPELLCHECK_DICTIONARIES_DIRECTORY


def get_all_possible_languages():
    locally_available = set(enchant.list_languages())
    downloadable = set(LANGUAGE_DOWNLOAD_URLS)
    return locally_available.union(downloadable)



def ensure_language_dictionary_available(lang_tag):
    if lang_tag in enchant.list_languages():
        return True
    elif lang_tag in LANGUAGE_DOWNLOAD_URLS:
        raise LanguageDictionaryDownloadable(lang_tag, LANGUAGE_DOWNLOAD_URLS[lang_tag])
    elif "_" in lang_tag:
        return ensure_language_dictionary_available(lang_tag.split("_")[0])
    else:
        raise LanguageDictionaryNotAvailable(lang_tag)


def download_language_dictionary(lang_tag, progress_callback, done_callback):
    download_url = get_language_dictionary_download_url(lang_tag)
    if download_url is None:
        raise ValueError(f"No download url for language {lang_tag}")
    THREAD_POOL_EXECUTOR.submit(
        _do_download__and_extract_lang_dictionary,
        download_url,
        progress_callback
    ).add_done_callback(partial(_done_callback, done_callback))


def get_language_dictionary_download_url(lang_tag):
    return LANGUAGE_DOWNLOAD_URLS.get(lang_tag)


def extract_language_dictionary_archive(file_buffer):
    hunspell_extraction_directory = os.path.join(SPELLCHECK_DICTIONARIES_DIRECTORY, "hunspell")
    if not os.path.isdir(hunspell_extraction_directory):
        os.mkdir(hunspell_extraction_directory)
    with zipfile.ZipFile(file_buffer, "r") as archive:
        members = [
            fname for fname in archive.namelist()
            if os.path.splitext(fname)[-1] in DICTIONARY_FILE_EXTS
        ]
        archive.extractall(hunspell_extraction_directory, members)


def _do_download__and_extract_lang_dictionary(download_url, progress_callback):
    file_buffer = BytesIO()
    with httpx.stream("GET", download_url) as response:
        total_size = int(response.headers["Content-Length"])
        for data in response.iter_bytes():
            file_buffer.write(data)
            progress = (response.num_bytes_downloaded / total_size) * 100
            progress_callback(int(progress))
    file_buffer.seek(0)
    extract_language_dictionary_archive(file_buffer)


def _done_callback(done_callback, future):
    if done_callback is None:
        return
    exception = future.exception()
    done_callback(exception)