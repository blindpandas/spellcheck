# coding: utf-8

# Copyright (c) 2021 Blind Pandas Team
# This file is covered by the GNU General Public License.

"""
  Spellcheck
  ~~~~~~~~~~~~~~~~~~~~~~

  The development of this addon is happening on GitHub <https://github.com/blindpandas/spellcheck>
"""

import api
import ui
import controlTypes
import globalPluginHandler
import eventHandler
import textInfos
import languageHandler
import winUser
from scriptHandler import script
from logHandler import log
from .language_dictionary import (
    set_enchant_language_dictionaries_directory,
    ensure_language_dictionary_available,
    LanguageDictionaryNotAvailable,
    LanguageDictionaryDownloadable
)
from .spellcheck_ui import SpellCheckMenu



import addonHandler
addonHandler.initTranslation()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_enchant_language_dictionaries_directory()

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
        treeInterceptor = obj.treeInterceptor
        if hasattr(treeInterceptor, 'TextInfo') and not treeInterceptor.passThrough:
            obj = treeInterceptor
        try:
            info = obj.makeTextInfo(textInfos.POSITION_SELECTION)
            return info.text
        except (RuntimeError, NotImplementedError):
            return ""

    @script(
        gesture="kb:nvda+alt+s",
        # translators: appears in the NVDA input help.
        description=_("Checks spelling errors for the selected text"),
        category="spellcheck"
    )
    def script_launch_testing(self, gesture):
        current_focus = api.getFocusObject()
        if not current_focus.states.intersection(
            {controlTypes.STATE_EDITABLE, controlTypes.STATE_MULTILINE}
        ):
            return
        selected_text = self.getSelectedText()
        if not selected_text.strip():
            # translators: the message is announced when there is no text is selected.
            ui.message(_("No text is selected"))
            return
        # Check the input language
        current_input_language  = self.get_input_language(api.getFocusObject().windowThreadID)
        try:
            ensure_language_dictionary_available(current_input_language)
        except LanguageDictionaryDownloadable as e:
            ui.message(f"You can download the language from: {e.download_url}")
            return
        except LanguageDictionaryNotAvailable as e:
            ui.message(f"Language dictionary for language {e.language} is not available.")
            return
        # Create our fake menu object
        misspellingsMenu = SpellCheckMenu(
            #translators: the name of the menu that shows up when the addon is being activated.
            name=_("Spelling Errors"),
            language_tag = current_input_language,
            text_to_process=selected_text
        )
        if not misspellingsMenu.items:
            # translators: announced when there are no spelling errors in a selected text.
            ui.message("No spelling mistakes")
            return
        eventHandler.queueEvent("gainFocus", misspellingsMenu)
