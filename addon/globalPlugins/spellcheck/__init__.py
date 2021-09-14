# coding: utf-8

# Copyright (c) 2021 Blind Pandas Team
# This file is covered by the GNU General Public License.

"""
  Spellcheck
  ~~~~~~~~~~~~~~~~~~~~~~

  The development of this addon is happening on GitHub <https://github.com/blindpandas/spellcheck>
"""

import tones
import wx
import api
import gui
import ui
import controlTypes
import globalPluginHandler
import queueHandler
import eventHandler
import textInfos
import languageHandler
import winUser
import NVDAObjects.behaviors
from contextlib import suppress
from scriptHandler import script
from logHandler import log
from .language_dictionary import (
    set_enchant_language_dictionaries_directory,
    get_all_possible_languages,
    ensure_language_dictionary_available,
    download_language_dictionary,
    LanguageDictionaryNotAvailable,
    LanguageDictionaryDownloadable
)
from .spellcheck_ui import SpellCheckMenu



import addonHandler
addonHandler.initTranslation()


class LanguageDictionaryDownloader:

    def __init__(self, language_tag):
        self.language_tag = language_tag
        self.language_description = languageHandler.getLanguageDescription(language_tag)
        self.progress_dialog = None

    def update_progress(self, progress):
        self.progress_dialog.Update(
            progress,
            _("Downloaded: {progress}%").format(progress=progress)
        )

    def done_callback(self, exception):
        self.progress_dialog.Hide()
        self.progress_dialog.Destroy()
        del self.progress_dialog
        wx.CallAfter(
            gui.messageBox,
            _("Successfully downloaded dictionary for  language {lang}").format(lang=self.language_description),
            _("Dictionary Downloaded"),
            style=wx.ICON_INFORMATION
        )

    def download(self):
        retval = gui.messageBox(
            _("Dictionary for language {lang} is missing.\nWould you like to download it?").format(lang=self.language_description),
            _("Download Language Dictionary"),
            style=wx.YES | wx.NO | wx.ICON_ASTERISK,
            parent=gui.mainFrame
        )
        if retval == wx.NO:
            return
        self.progress_dialog  = wx.ProgressDialog(
            title=_("Downloading Dictionary For Language {lang}").format(lang=self.language_description),
            message=_("Downloading. Please wait"),
            parent=gui.mainFrame,
        )
        self.progress_dialog.CenterOnScreen()
        download_language_dictionary(self.language_tag, self.update_progress, self.done_callback)



class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_enchant_language_dictionaries_directory()

    @script(
        gesture="kb:nvda+alt+s",
        # translators: appears in the NVDA input help.
        description=_("Checks spelling errors for the selected text using the current input language"),
        category="spellcheck"
    )
    def script_spellcheck_based_on_current_input_language(self, gesture):
        text = self.getSelectedText()
        if text:
            current_input_language  = self.get_input_language(api.getFocusObject().windowThreadID)
            self.spellcheck(current_input_language, text)

    def spellcheck(self, language_tag, text_to_spellcheck):
        try:
            ensure_language_dictionary_available(language_tag)
        except LanguageDictionaryDownloadable as e:
            wx.CallAfter(LanguageDictionaryDownloader(e.language).download)
            return
        except LanguageDictionaryNotAvailable as e:
            lang = languageHandler.getLanguageDescription(e.language)
            if lang is None:
                lang = e.language
            queueHandler.queueFunction(
                queueHandler.eventQueue,
                ui.message, _("Language dictionary for language {lang} is not available.").format(lang=lang)
            )
            return
        # Create our fake menu object
        misspellingsMenu = SpellCheckMenu(
            #translators: the name of the menu that shows up when the addon is being activated.
            name=_("Spelling Errors"),
            language_tag=language_tag,
            text_to_process=text_to_spellcheck
        )
        if not misspellingsMenu.items:
            # translators: announced when there are no spelling errors in a selected text.
            ui.message("No spelling mistakes")
            return
        eventHandler.queueEvent("gainFocus", misspellingsMenu)

    @staticmethod
    def get_input_language(thread_id):
        kbdlid = winUser.getKeyboardLayout(thread_id)
        windows_lcid = kbdlid & (2**16 - 1)
        return languageHandler.windowsLCIDToLocaleName(windows_lcid)

    @staticmethod
    def getSelectedText() -> str:
        """Retrieve the selected text.
        @rtype: str
        """
        obj = api.getFocusObject()
        # Restrict the selection to editable text only
        if not isinstance(obj, NVDAObjects.behaviors.EditableText):
            return
        treeInterceptor = obj.treeInterceptor
        if hasattr(treeInterceptor, 'TextInfo') and not treeInterceptor.passThrough:
            obj = treeInterceptor
        text = ""
        with suppress(RuntimeError, NotImplementedError):
            info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
            text = info.text
        if not text.strip():
            # translators: the message is announced when there is no text is selected.
            ui.message(_("No text is selected"))
        return text
