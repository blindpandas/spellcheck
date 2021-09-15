# coding: utf-8

# Copyright (c) 2021 Blind Pandas Team
# This file is covered by the GNU General Public License.

import math
import os
import globalVars
import languageHandler
from io import BytesIO
from functools import partial
from logHandler import log
from .helpers import import_bundled_library, DATA_DIRECTORY


with import_bundled_library():
    import enchant
    import httpx
    from concurrent.futures import ThreadPoolExecutor


# Constants
DICT_GITHUB_API_URL = "https://api.github.com/repos/LibreOffice/dictionaries/contents/{lang_tag}?ref=master"
DICTIONARY_FILE_EXTS = {
    ".dic",
    ".aff",
}
THREAD_POOL_EXECUTOR = ThreadPoolExecutor()
SPELLCHECK_DICTIONARIES_DIRECTORY = os.path.join(
    globalVars.appArgs.configPath, "spellcheck_dictionaries"
)
with open(os.path.join(DATA_DIRECTORY, "downloadable_languages.txt"), "r") as file:
    DOWNLOADABLE_LANGUAGES = [tag.strip() for tag in file if tag.strip()]


class LanguageDictionaryNotAvailable(LookupError):
    """Raised when the given language has no dictionary."""

    def __init__(self, language):
        self.language = language


class LanguageDictionaryDownloadable(LanguageDictionaryNotAvailable):
    """Raised if the language dictionary is unavailable locally, but available for download."""


class MultipleDownloadableLanguagesFound(LanguageDictionaryDownloadable):
    """Raised if more than one variant are available for download."""

    def __init__(self, language, available_variances, *args, **kwargs):
        super().__init__(language, *args, **kwargs)
        self.available_variances = available_variances


def set_enchant_language_dictionaries_directory():
    if not os.path.isdir(SPELLCHECK_DICTIONARIES_DIRECTORY):
        os.mkdir(SPELLCHECK_DICTIONARIES_DIRECTORY)
    os.environ["ENCHANT_CONFIG_DIR"] = SPELLCHECK_DICTIONARIES_DIRECTORY


def get_all_possible_languages():
    return set(DOWNLOADABLE_LANGUAGES)


def get_enchant_language_dictionary(lang_tag):
    try:
        return enchant.request_dict(lang_tag)
    except enchant.errors.DictNotFoundError:
        if lang_tag in DOWNLOADABLE_LANGUAGES:
            raise LanguageDictionaryDownloadable(lang_tag)
        elif "_" in lang_tag:
            return get_enchant_language_dictionary(lang_tag.split("_")[0])
        else:
            if len(lang_tag) == 2:
                available_variances = [
                    downloadable_lang
                    for downloadable_lang in DOWNLOADABLE_LANGUAGES
                    if downloadable_lang.split("_")[0] == lang_tag
                ]
                if available_variances:
                    raise MultipleDownloadableLanguagesFound(
                        language=lang_tag, available_variances=available_variances
                    )
    raise LanguageDictionaryNotAvailable(lang_tag)


def download_language_dictionary(lang_tag, progress_callback, done_callback):
    if lang_tag not in DOWNLOADABLE_LANGUAGES:
        raise ValueError(f"Language {lang_tag} is not available for download")
    THREAD_POOL_EXECUTOR.submit(
        _do_download__and_extract_lang_dictionary, lang_tag, progress_callback
    ).add_done_callback(partial(_done_callback, done_callback))


def get_language_dictionary_download_info(lang_tag):
    directory_listing = httpx.get(DICT_GITHUB_API_URL.format(lang_tag=lang_tag)).json()
    return {
        entry["name"]: (entry["download_url"], entry["size"])
        for entry in directory_listing
        if os.path.splitext(entry["name"])[-1] in DICTIONARY_FILE_EXTS
    }


def _do_download__and_extract_lang_dictionary(lang_tag, progress_callback):
    download_info = get_language_dictionary_download_info(lang_tag)
    name_to_buffer = {}
    total_size = sum(filesize for (n, (u, filesize)) in download_info.items())
    downloaded_til_now = 0
    for (filename, (download_url, file_size)) in download_info.items():
        with httpx.Client() as client:
            with client.stream("GET", download_url) as response:
                file_buffer = BytesIO()
                for data in response.iter_bytes():
                    file_buffer.write(data)
                    downloaded_til_now += len(data)
                    progress = math.floor((downloaded_til_now / total_size) * 100)
                    progress_callback(progress)
                file_buffer.seek(0)
                name_to_buffer[filename] = file_buffer
    # Now copy the downloaded file to the destination
    hunspell_extraction_directory = os.path.join(
        SPELLCHECK_DICTIONARIES_DIRECTORY, "hunspell"
    )
    if not os.path.isdir(hunspell_extraction_directory):
        os.mkdir(hunspell_extraction_directory)
    for (filename, file_buffer) in name_to_buffer.items():
        full_file_path = os.path.join(hunspell_extraction_directory, filename)
        with open(full_file_path, "wb") as output_file:
            output_file.write(file_buffer.getvalue())


def _done_callback(done_callback, future):
    if done_callback is None:
        return
    try:
        result = future.result()
        done_callback(None)
    except httpx.HTTPError:
        done_callback(ConnectionError("Failed to get language dictionary"))
    except Exception as e:
        done_callback(e)
