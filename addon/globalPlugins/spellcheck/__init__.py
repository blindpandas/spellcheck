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
import globalVars
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
from .helpers import play_sound
from .language_dictionary import (
    set_enchant_language_dictionaries_directory,
    get_all_possible_languages,
    get_enchant_language_dictionary,
    download_language_dictionary,
    LanguageDictionaryNotAvailable,
    LanguageDictionaryDownloadable,
    MultipleDownloadableLanguagesFound,
)
from .spellcheck_ui import SpellCheckMenu, SCRCAT__SPELLCHECK


import addonHandler

addonHandler.initTranslation()


class LanguageChoiceDialog(wx.SingleChoiceDialog):
    def __init__(self, language_tags, *args, **kwargs):
        self.language_tags = tuple(sorted(language_tags))
        choices = [
            languageHandler.getLanguageDescription(l) for l in self.language_tags
        ]
        kwargs["choices"] = choices
        super().__init__(*args, **kwargs)

    def ShowModal(self):
        globalVars.LANGUAGE_DIALOG_SHOWN = True
        retval = super().ShowModal()
        globalVars.LANGUAGE_DIALOG_SHOWN = False
        if retval == wx.ID_OK:
            return self.language_tags[self.GetSelection()]


class LanguageDictionaryDownloader:
    def __init__(self, language_tag, ask_user=True):
        self.language_tag = language_tag
        self.ask_user = ask_user
        self.language_description = languageHandler.getLanguageDescription(language_tag)
        self.progress_dialog = None

    def update_progress(self, progress):
        self.progress_dialog.Update(
            progress,
            # Translators: message of a progress dialog
            _("Downloaded: {progress}%").format(progress=progress),
        )

    def done_callback(self, exception):
        self.progress_dialog.Hide()
        self.progress_dialog.Destroy()
        del self.progress_dialog
        if exception is None:
            wx.CallAfter(
                gui.messageBox,
                _("Successfully downloaded dictionary for  language {lang}").format(
                    lang=self.language_description
                ),
                _("Dictionary Downloaded"),
                style=wx.ICON_INFORMATION,
            )
        else:
            wx.CallAfter(
                gui.messageBox,
                _(
                    "Cannot download dictionary for language {lang}.\nPlease check your connection and try again."
                ).format(lang=self.language_description),
                _("Download Failed"),
                style=wx.ICON_ERROR,
            )
            log.exception(
                f"Failed to download language dictionary.\nException: {exception}"
            )

    def download(self):
        if self.ask_user:
            retval = gui.messageBox(
                _(
                    "Dictionary for language {lang} is missing.\nWould you like to download it?"
                ).format(lang=self.language_description),
                _("Download Language Dictionary"),
                style=wx.YES | wx.NO | wx.ICON_ASTERISK,
                parent=gui.mainFrame,
            )
            if retval == wx.NO:
                return
        self.progress_dialog = wx.ProgressDialog(
            # Translators: title of a progress dialog
            title=_("Downloading Dictionary For Language {lang}").format(
                lang=self.language_description
            ),
            # Translators: message of a progress dialog
            message=_("Retrieving download information..."),
            parent=gui.mainFrame,
        )
        self.progress_dialog.CenterOnScreen()
        download_language_dictionary(
            self.language_tag, self.update_progress, self.done_callback
        )


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_enchant_language_dictionaries_directory()
        self._active_spellcheck_language = None

    def on_language_variance_download(self, lang_tag):
        wx.CallAfter(LanguageDictionaryDownloader(lang_tag, ask_user=False).download)

    def on_user_chosen_language(self, lang_tag):
        self._active_spellcheck_language = lang_tag
        self.obtain_language_dictionary(lang_tag)

    @script(
        gesture="kb:nvda+alt+s",
        # translators: appears in the NVDA input help.
        description=_(
            "Checks spelling errors for the selected text using the current input language"
        ),
        category=SCRCAT__SPELLCHECK,
    )
    def script_spellcheck_text(self, gesture):
        text = self.getSelectedText()
        if not text:
            return
        if self._active_spellcheck_language is None:
            spellcheck_language = self.get_input_language(
                api.getFocusObject().windowThreadID
            )
        else:
            spellcheck_language = self._active_spellcheck_language
        self.spellcheck(spellcheck_language, text)

    @script(
        gesture="kb:nvda+alt+shift+l",
        # translators: appears in the NVDA input help.
        description=_(
            "Toggles the method used in determining the language for spellchecking: user-chosen versus current input language"
        ),
        category=SCRCAT__SPELLCHECK,
    )
    def script_toggle_user_chosen_spellcheck_language(self, gesture):
        if getattr(globalVars, "LANGUAGE_DIALOG_SHOWN", False):
            queueHandler.queueFunction(
                queueHandler.eventQueue,
                ui.message,
                # Translators: spoken message when the dialog is already open
                _("Dialog is already open")
            )
            return
        if self._active_spellcheck_language is None:
            lang_choice_dialog = LanguageChoiceDialog(
                get_all_possible_languages(),
                gui.mainFrame,
                # Translators: message of a dialog containing language choices
                _("Please choose the language you want to use for spellchecking."),
                # Translators: title of a dialog containing a list of languages
                _("Choose Spellcheck Language"),
            )
            gui.runScriptModalDialog(
                lang_choice_dialog,
                self.on_user_chosen_language,
            )
        else:
            self._active_spellcheck_language = None
            # Translators: spoken message when toggling the way the spellcheck language is determined
            queueHandler.queueFunction(
                queueHandler.eventQueue,
                ui.message,
                _("Using the active Input language for spellchecking"),
            )

    def spellcheck(self, language_tag, text_to_spellcheck):
        language_dictionary = self.obtain_language_dictionary(language_tag)
        if not language_dictionary:
            return
        # Create our fake menu object
        misspellingsMenu = SpellCheckMenu(
            # translators: the name of the menu that shows up when the addon is being activated.
            name=_("Spelling Errors"),
            language_dictionary=language_dictionary,
            text_to_process=text_to_spellcheck,
        )
        if not misspellingsMenu.items:
            # translators: announced when there are no spelling errors in a selected text.
            ui.message("No spelling mistakes")
            return
        eventHandler.queueEvent("gainFocus", misspellingsMenu)
        queueHandler.queueFunction(
            queueHandler.eventQueue,
            play_sound,
            "menu_open"
        )

    def obtain_language_dictionary(self, language_tag):
        try:
            return get_enchant_language_dictionary(language_tag)
        except MultipleDownloadableLanguagesFound as e:
            choice_dialog = LanguageChoiceDialog(
                e.available_variances,
                gui.mainFrame,
                # Translators: message of a dialog containing language choices
                _(
                    "Dialects found for language {lang}.\nPlease select the one you want to download."
                ).format(lang=languageHandler.getLanguageDescription(e.language)),
                # Translators: title of a dialog containing a list of languages
                _("Dialects Found"),
            )
            gui.runScriptModalDialog(choice_dialog, self.on_language_variance_download)
        except LanguageDictionaryDownloadable as e:
            wx.CallAfter(LanguageDictionaryDownloader(e.language).download)
        except LanguageDictionaryNotAvailable as e:
            lang = languageHandler.getLanguageDescription(e.language)
            if lang is None:
                lang = e.language
            queueHandler.queueFunction(
                queueHandler.eventQueue,
                ui.message,
                _("Language dictionary for language {lang} is not available.").format(
                    lang=lang
                ),
            )
        return False

    @staticmethod
    def get_input_language(thread_id):
        kbdlid = winUser.getKeyboardLayout(thread_id)
        windows_lcid = kbdlid & (2 ** 16 - 1)
        return languageHandler.windowsLCIDToLocaleName(windows_lcid)

    @staticmethod
    def getSelectedText() -> str:
        """Retrieve the selected text."""
        obj = api.getFocusObject()
        # Restrict the selection to editable text only
        if not isinstance(obj, NVDAObjects.behaviors.EditableText):
            # translators: the message is announced when there is no text is selected.
            queueHandler.queueFunction(
                queueHandler.eventQueue,
                ui.message,
                _("Spellchecking is not supported here"),
            )
            return
        treeInterceptor = obj.treeInterceptor
        if hasattr(treeInterceptor, "TextInfo") and not treeInterceptor.passThrough:
            obj = treeInterceptor
        text = ""
        with suppress(RuntimeError, NotImplementedError):
            info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
            text = info.text.strip()
        if not text:
            # translators: the message is announced when there is no text is selected.
            queueHandler.queueFunction(
                queueHandler.eventQueue, ui.message, _("No text is selected")
            )
        return text
