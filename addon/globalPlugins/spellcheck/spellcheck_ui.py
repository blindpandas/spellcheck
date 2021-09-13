# coding: utf-8

"""
This is the implemented user experience:
* Left/right arrows navigate between misspellings
* Up/down arrows navigate between suggestions
When misspelling items are focused:
    * Enter sets focus to the suggestions menu
    * Backspace rejects the suggestion and clear the acceptance status
When suggestions are focused:
    * Enter accepts the currently focused suggestion and set focus to the misspelling item

Notes:
* Implement the text replacement logic in the close_menu method in the SpellCheckMenu class
* The code makes heavy use of class inheritance to achieve conciseness (and elegance)
* Accepting the suggestion will change the description of the misspelling item, and rejecting the suggestion will remove the description
* Note that the position info of the items in all of the menus is correctly provided (i.e. item 1 of 2)
"""

import tones
import sys
import os
import api
import ui
import controlTypes
import queueHandler
import eventHandler
import globalPluginHandler
import speech
from enum import Enum, auto
from contextlib import suppress
from NVDAObjects import NVDAObject
from keyboardHandler import  KeyboardInputGesture
from scriptHandler import script
from logHandler import log
from textInfos import POSITION_SELECTION


# Add the current directory to sys.path, import enchant, and remove the current directory from sys.path
plugin_directory = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, plugin_directory)
from enchant .checker import SpellChecker
sys.path.remove(plugin_directory)


# This should be set to Tru in the final release 
# It prevent any key strokes from reaching the application
# Thereby avoiding any unintentional edits to the underlying text control
CAPTURE_KEYS_WHILE_IN_FOCUS = False


class UserChoiceType(Enum):
    """
    We use these flags to determine and store the type of
    item the user has chosen from the suggestions menu.
    """
    SUGGESTION = auto()
    NO_SUGGESTION = auto()
    IGNORE_ONCE = auto()
    IGNORE_ALL = auto()
    ADD_TO_PERSONAL_DICTIONARY = auto()


class KeyboardNavigableNVDAObjectMixin:
    windowClassName = ""
    windowControlID = 0
    windowThreadID = 0

    def script_do_nothing(self, gesture):
        pass

    def getScript(self, gesture):
        """Ensures that no keys are sent to the underlying text control."""
        script = NVDAObject.getScript(self, gesture)
        if CAPTURE_KEYS_WHILE_IN_FOCUS and script is None:
            return self.script_do_nothing
        return script


class ItemContainerMixin:
    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return iter(self.items)

    def index_of(self, item):
        items_hashes = [hash(i) for i in self.items]
        item_hash = hash(item)
        if item_hash in items_hashes:
            return items_hashes.index(item_hash)

    def init_container_state(self, items, on_top_edge=None, on_bottom_edge=None):
        self.items = items
        self.children = items
        self.controllerFor = self.children
        self.on_top_edge = on_top_edge
        self.on_bottom_edge = on_bottom_edge
        self._current_index = 0

    def set_current(self, index):
        if index not in range(len(self)):
            raise ValueError("Index out of range")
        self._current_index = index

    def get_item(self, index):
        with suppress(IndexError):
            return self.items[index]

    def get_current_item(self):
        return self.get_item(self._current_index)

    def go_to_next(self):
        item = self.get_item(self._current_index + 1)
        if item is not None:
            self._current_index += 1
        elif self.items:
            if self.on_bottom_edge is not None:
                self.on_bottom_edge()
                return
            else:
                item = self.items[-1]
        return item

    def go_to_prev(self):
        prev_index = self._current_index - 1
        if prev_index >= 0:
            item = self.get_item(prev_index)
            if item is not None:
                self._current_index = prev_index
        else:
            if self.on_top_edge is not None:
                self.on_top_edge()
                return
            elif len(self.items) > 0:
                item = self.items[0]
        return item


class MenuItemObject(KeyboardNavigableNVDAObjectMixin, NVDAObject):
    role = controlTypes.ROLE_MENUITEM

    def __init__(self, parent, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        self.processID = self.parent.processID
        self.name = name

    @property
    def positionInfo(self):
        return {
            "indexInGroup": self.parent.index_of(self) + 1,
            "similarItemsInGroup": len(self.parent),
        }

    def go_to_next(self):
        item = self.parent.go_to_next()
        if item is not None:
            eventHandler.queueEvent("gainFocus", item)

    def go_to_prev(self):
        item = self.parent.go_to_prev()
        if item is not None:
            eventHandler.queueEvent("gainFocus", item)

    @script(gesture="kb:escape")
    def script_close_menu(self, gesture):
        self.parent.close_menu()


class MisspellingMenuItemObject(MenuItemObject):

    def __init__(self, suggestions, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.suggestions = suggestions
        # Save this here
        self.original_misspelling = self.name
        self._user_choice = None

    def get_replacement_info(self):
        if self._user_choice is not None:
            choice_type = self._user_choice.choice_type
            choice_value = None if choice_type is not UserChoiceType.SUGGESTION else self._user_choice.name
        else:
            choice_type = UserChoiceType.IGNORE_ONCE
            choice_value = None
        return (self.original_misspelling, choice_type, choice_value)

    def on_user_choice(self, choice):
        self._user_choice = choice
        if choice.choice_type is UserChoiceType.SUGGESTION:
            # translators: appears between the misspelled word and the selected suggestion by the user.
            desc = _(f"accepted: {choice.name}")
        elif choice.choice_type is UserChoiceType.IGNORE_ONCE:
            #translators: appears in the spelling error menu if a user chooses to ignore the error once.
            desc = "Ignored once"
        elif choice.choice_type is UserChoiceType.IGNORE_ALL:
            #translators: appears in the spelling error menu if a user chooses to ignore all appearance of that word.
            desc = _("Ignored all")
        elif choice.choice_type is UserChoiceType.ADD_TO_PERSONAL_DICTIONARY:
            #translators: appears in the misspelled words menu when a user chooses to add the erroneous word to the personal dictionary.
            desc = _("Added to personal dictionary")
        else:
            desc = self.description
        self.description = desc
        self.back_to_misspelling()

    def back_to_misspelling(self):
        eventHandler.queueEvent("suggestionsClosed", self.parent.parent)
        eventHandler.queueEvent("gainFocus", self.parent)

    @property
    def suggestions_menu(self):
        self._suggestions_menu = MenuObject(name="Suggestions")
        common_kwargs = {
            "acceptance_callback": self.on_user_choice,
            "parent": self._suggestions_menu,
        }
        menu_items = [
            SuggestionMenuItemObject(
                choice_type=UserChoiceType.SUGGESTION,
                name=item,
                **common_kwargs
            )
            for item in self.suggestions
        ]
        if not menu_items:
            # No suggestions
            no_suggestions_item = SuggestionMenuItemObject(
                choice_type=UserChoiceType.NO_SUGGESTION,
                name="No Suggestions",
                **common_kwargs
            )
            no_suggestions_item.states = {controlTypes.STATE_UNAVAILABLE,}
            menu_items.append(no_suggestions_item)
        menu_items.extend([
            SuggestionMenuItemObject(
                choice_type=UserChoiceType.IGNORE_ONCE,
                #translators: name of the option in the suggestion menu
                name=_("Ignore once"),
                **common_kwargs
            ),
            SuggestionMenuItemObject(
                choice_type=UserChoiceType.IGNORE_ALL,
                #translators: name of the option in the suggestion menu.
                name=_("Ignore all"),
                **common_kwargs
            ),
            SuggestionMenuItemObject(
                choice_type=UserChoiceType.ADD_TO_PERSONAL_DICTIONARY,
                #translators: name of the option in the suggestion menu.
                name=_("Add to dictionary"),
                **common_kwargs
            ),
        ])
        self._suggestions_menu.init_container_state(
            menu_items,
            on_top_edge=self.back_to_misspelling,
        )
        return self._suggestions_menu

    @script(gesture="kb:backspace")
    def script_backspace(self, gesture):
        """Reject suggestion"""
        if self._user_choice is not None:
            self._user_choice = None
            self.description = ""
            eventHandler.queueEvent("gainFocus", self)

    @script(gesture="kb:rightarrow")
    def script_rightarrow(self, gesture):
        self.go_to_next()

    @script(gesture="kb:leftarrow")
    def script_leftarrow(self, gesture):
        self.go_to_prev()

    @script(gesture="kb:downarrow")
    def script_downarrow(self, gesture):
        self.suggestions_menu.set_current(0)
        eventHandler.queueEvent("suggestionsOpened", self.parent.parent)
        eventHandler.queueEvent("gainFocus", self.suggestions_menu)

    @script(gesture="kb:enter")
    def script_enter(self, gesture):
        self.script_downarrow(gesture)

    @script(gesture="kb:control+c")
    def script_copy_corrected_text(self, gesture):
        self.parent.copy_to_clipboard()

    @script(gesture="kb:control+r")
    def script_replace_text(self, gesture):
        self.parent.replace_text()


class SuggestionMenuItemObject(MenuItemObject):
    """
    The most important attribute is the type of the item.
    The type is used to determine appropriate action in the spellChecker class.
    """

    def __init__(self, choice_type, acceptance_callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choice_type = choice_type
        self.acceptance_callback = acceptance_callback

    @script(gesture="kb:downarrow")
    def script_downarrow(self, gesture):
        self.go_to_next()

    @script(gesture="kb:uparrow")
    def script_uparrow(self, gesture):
        self.go_to_prev()

    @script(gesture="kb:enter")
    def script_accept_suggestion(self, gesture):
        self.acceptance_callback(self)


class MenuObject(KeyboardNavigableNVDAObjectMixin, ItemContainerMixin, NVDAObject):
    role = controlTypes.ROLE_MENU

    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.parent = api.getFocusObject()
        self.processID = self.parent.processID

    def close_menu(self):
        eventHandler.queueEvent("gainFocus", self.parent)

    def event_gainFocus(self):
        speech.speakObject(self, controlTypes.OutputReason.FOCUS)
        eventHandler.queueEvent("gainFocus", self.get_current_item())


class SpellCheckMenu(MenuObject):
    """This is a special menu object."""

    def __init__(self, text_to_process, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Keep reference to the text to reinitialize the SpellChecker a second time
        self.lang = "en_US"
        self.text_to_process = text_to_process
        # This is not an instance variable!
        spellchecker = self.make_spellchecker(self.lang, self.text_to_process)
        self.init_container_state(
            # Here we consume our SpellChecker for the first time
            # If you did a for-loop after this line, you'll get nothing
            items=[MisspellingMenuItemObject(parent=self, name=item.word, suggestions=item.suggest()) for item in spellchecker]
        )

    @staticmethod
    def make_spellchecker(lang, text):
        spellchecker = SpellChecker(lang)
        spellchecker.set_text(text)
        return spellchecker

    def get_corrected_text(self):
        # We should reinitialize the spellChecker class with the same text we used to initialize it in the first place
        spellchecker = self.make_spellchecker(self.lang, self.text_to_process)
        replacement_info = [misspelling.get_replacement_info() for misspelling in self]
        for (chk, replacement_info) in zip(spellchecker, replacement_info):
            misspelling, choice_type, choice_value = replacement_info
            # Sanity check. Remove
            if chk.word != misspelling:
                tones.beep(400, 400)
            if choice_type is UserChoiceType.SUGGESTION:
                chk.replace(choice_value)
            elif choice_type is UserChoiceType.IGNORE_ONCE:
                chk.replace(misspelling)
            elif choice_type is UserChoiceType.IGNORE_ALL:
                chk.ignore_always()
            elif choice_type is UserChoiceType.ADD_TO_PERSONAL_DICTIONARY:
                chk.add()
        return spellchecker.get_text()

    def close_menu(self):
        super().close_menu()

    def copy_to_clipboard(self):
        api.copyToClip(self.get_corrected_text(), True)
        self.close_menu()

    def replace_text(self):
        """
        Not sure whether it will work or not 
        At least it requires the user to select the text, which is required anyway.
        Also, as a side effect, it copies the text to the clipboard.
        """
        api.copyToClip(self.get_corrected_text())
        paste_gesture = KeyboardInputGesture.fromName("control+v")
        eventHandler.executeEvent("gainFocus", self.parent)
        paste_gesture.send()
        eventHandler.queueEvent("gainFocus", self.parent)


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

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
            info = obj.makeTextInfo(POSITION_SELECTION)
        except (RuntimeError, NotImplementedError):
            info = None
        return info.text

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
            ui.message_(("No text is selected"))
            return
        # Create our fake menu object
        misspellingsMenu = SpellCheckMenu(
            #translators: the name of the menu that shows up when the addon is being activated.
            name=_("Spelling Errors"),
            text_to_process=selected_text
        )
        if not misspellingsMenu.items:
            # translators: announced when there are no spelling errors in a selected text.
            ui.message("No spelling mistakes")
            return
        eventHandler.queueEvent("gainFocus", misspellingsMenu)
