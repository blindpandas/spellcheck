# coding: utf-8

# Copyright (c) 2021 Blind Pandas Team
# This file is covered by the GNU General Public License.

import os
import tones
import api
import ui
import controlTypes
import speech
import queueHandler
import eventHandler
from enum import Enum, auto
from contextlib import suppress
from NVDAObjects import NVDAObject
from NVDAObjects.behaviors import (
    EditableTextWithAutoSelectDetection,
    EditableTextWithSuggestions,
)
from keyboardHandler import KeyboardInputGesture
from scriptHandler import script
from logHandler import log
from .helpers import import_bundled_library, play_sound


with import_bundled_library():
    from cached_property import cached_property
    from enchant.checker import SpellChecker


# This should be set to Tru in the final release
# It prevent any key strokes from reaching the application
# Thereby avoiding any unintentional edits to the underlying text control
CAPTURE_KEYS_WHILE_IN_FOCUS = True
PASTE_GESTURE = KeyboardInputGesture.fromName("control+v")


import addonHandler

addonHandler.initTranslation()


# Translators: script category for Spellcheck add-on
SCRCAT__SPELLCHECK = _("Spellcheck")


class UserChoiceType(Enum):
    """
    We use these flags to determine and store the type of
    item the user has chosen from the suggestions menu.
    """

    SUGGESTION = auto()
    NO_ACTION = auto()
    IGNORE_FOR_THIS_SESSION = auto()
    ADD_TO_PERSONAL_DICTIONARY = auto()


class KeyboardNavigableNVDAObjectMixin:
    windowClassName = ""
    windowControlID = 0
    windowThreadID = -1
    windowHandle = -1

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

    def remove_item(self, item):
        item_index = self.index_of(item)
        self.items.pop(item_index)

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


class FakeEditableNVDAObject(
    KeyboardNavigableNVDAObjectMixin, EditableTextWithSuggestions, NVDAObject
):
    role = controlTypes.ROLE_EDITABLETEXT
    states = {
        controlTypes.STATE_EDITABLE,
        controlTypes.STATE_FOCUSABLE,
        controlTypes.STATE_FOCUSED,
    }
    processID = os.getpid()


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
    def __init__(self, lang_dict, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lang_dict = lang_dict
        # Save this here
        self.original_misspelling = self.name
        self._user_choice = None

    @cached_property
    def suggestions(self):
        return self.lang_dict.suggest(self.original_misspelling)

    def get_replacement_info(self):
        if self._user_choice is not None:
            choice_type = self._user_choice.choice_type
            choice_value = (
                None
                if choice_type is not UserChoiceType.SUGGESTION
                else self._user_choice.name
            )
        else:
            choice_type = UserChoiceType.NO_ACTION
            choice_value = None
        return (self.original_misspelling, choice_type, choice_value)

    def on_user_choice(self, choice):
        self._user_choice = choice
        if choice.choice_type is UserChoiceType.SUGGESTION:
            # translators: appears between the misspelled word and the selected suggestion by the user.
            desc = _(f"accepted: {choice.name}")
        elif choice.choice_type is UserChoiceType.IGNORE_FOR_THIS_SESSION:
            eventHandler.queueEvent("suggestionsClosed", FakeEditableNVDAObject())
            self.parent.ignore_for_this_session(self)
            return
        elif choice.choice_type is UserChoiceType.ADD_TO_PERSONAL_DICTIONARY:
            # translators: appears in the misspelled words menu when a user chooses to add the erroneous word to the personal dictionary.
            desc = _("Added to personal dictionary")
        else:
            desc = self.description
        self.description = desc
        self.back_to_misspelling()

    def back_to_misspelling(self):
        eventHandler.queueEvent("suggestionsClosed", FakeEditableNVDAObject())
        eventHandler.queueEvent("gainFocus", self.parent)

    @cached_property
    def suggestions_menu(self):
        self._suggestions_menu = SuggestionsMenu(name="Suggestions")
        common_kwargs = {
            "acceptance_callback": self.on_user_choice,
            "parent": self._suggestions_menu,
        }
        menu_items = [
            SuggestionMenuItemObject(
                choice_type=UserChoiceType.SUGGESTION, name=item, **common_kwargs
            )
            for item in self.suggestions
        ]
        if not menu_items:
            # No suggestions
            no_suggestions_item = SuggestionMenuItemObject(
                choice_type=UserChoiceType.NO_ACTION,
                name="No Suggestions",
                **common_kwargs,
            )
            no_suggestions_item.states = {
                controlTypes.STATE_UNAVAILABLE,
            }
            menu_items.append(no_suggestions_item)
        menu_items.extend(
            [
                SuggestionMenuItemObject(
                    choice_type=UserChoiceType.IGNORE_FOR_THIS_SESSION,
                    # translators: name of the option in the suggestion menu
                    name=_("Ignore for this session"),
                    **common_kwargs,
                ),
                SuggestionMenuItemObject(
                    choice_type=UserChoiceType.ADD_TO_PERSONAL_DICTIONARY,
                    # translators: name of the option in the suggestion menu.
                    name=_("Add to dictionary"),
                    **common_kwargs,
                ),
            ]
        )
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
        eventHandler.queueEvent("suggestionsOpened", FakeEditableNVDAObject())
        eventHandler.queueEvent("gainFocus", self.suggestions_menu)

    @script(gesture="kb:enter")
    def script_enter(self, gesture):
        self.script_downarrow(gesture)

    @script(
        gesture="kb:control+c",
        # translators: appears in the NVDA input help.
        description=_("Copies the corrected text to the clipboard"),
        category=SCRCAT__SPELLCHECK,
    )
    def script_copy_corrected_text(self, gesture):
        self.parent.copy_to_clipboard()

    @script(
        gesture="kb:control+r",
        # translators: appears in the NVDA input help.
        description=_("Replaces the text in the edit field with the corrected text"),
        category=SCRCAT__SPELLCHECK,
    )
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


class SuggestionsMenu(MenuObject):
    def close_menu(self):
        eventHandler.queueEvent("suggestionsClosed", FakeEditableNVDAObject())
        eventHandler.queueEvent("gainFocus", self.parent.parent)


class SpellCheckMenu(MenuObject):
    """This is a special menu object."""

    def __init__(self, language_dictionary, text_to_process, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.language_dictionary = language_dictionary
        self.text_to_process = text_to_process
        spellchecker = self.make_spellchecker(
            self.language_dictionary, self.text_to_process
        )
        misspelling_menu_items = [
            MisspellingMenuItemObject(
                parent=self, name=item.word, lang_dict=spellchecker.dict
            )
            for item in spellchecker
        ]
        self.init_container_state(
            # Here we consume our SpellChecker for the first time
            # If you did a for-loop after this line, you'll get nothing
            items=misspelling_menu_items
        )
        # A list of ignored words in this session
        self._ignored_words = []

    def make_spellchecker(self, language_dictionary, text):
        spellchecker = SpellChecker(language_dictionary)
        spellchecker.set_text(text)
        return spellchecker

    def get_corrected_text(self):
        # We should reinitialize the spellChecker class with the same text we used to initialize it in the first place
        spellchecker = self.make_spellchecker(
            self.language_dictionary, self.text_to_process
        )
        for ignored_word in self._ignored_words:
            spellchecker.ignore_always(ignored_word)
        replacement_info = [misspelling.get_replacement_info() for misspelling in self]
        for (chk, replacement_info) in zip(spellchecker, replacement_info):
            misspelling, choice_type, choice_value = replacement_info
            # Sanity check. Remove
            if chk.word != misspelling:
                tones.beep(400, 400)
            if choice_type is UserChoiceType.SUGGESTION:
                chk.replace(choice_value)
            elif choice_type is UserChoiceType.ADD_TO_PERSONAL_DICTIONARY:
                chk.add()
        return spellchecker.get_text()

    def ignore_for_this_session(self, item):
        misspelling = item.original_misspelling
        self._ignored_words.append(misspelling)
        current_focus_index = self.index_of(item)
        items_to_remove = [
            menu_item
            for menu_item in self
            if menu_item.original_misspelling == misspelling
        ]
        for rmv_item in items_to_remove:
            self.remove_item(rmv_item)
        if self:
            self.set_current(0)
            eventHandler.queueEvent("gainFocus", self)
        else:
            queueHandler.queueFunction(
                queueHandler.eventQueue, ui.message, _("No misspellings")
            )
            self.close_menu()

    def copy_to_clipboard(self):
        api.copyToClip(self.get_corrected_text(), True)
        self.close_menu()

    def replace_text(self):
        try:
            old_clipboard_text = api.getClipData()
        except:
            old_clipboard_text = None
        is_readonly = controlTypes.STATE_READONLY in self.parent.states
        if is_readonly:
            # translators: spoken message
            queueHandler.queueFunction(
                queueHandler.eventQueue,
                ui.message,
                _("Can not replace text, the text field is read only"),
            )
            queueHandler.queueFunction(
                queueHandler.eventQueue, api.setFocusObject, self.parent
            )
            queueHandler.queueFunction(
                queueHandler.eventQueue,
                speech.speakObject,
                self.parent,
                controlTypes.OutputReason.FOCUS,
            )
        else:
            api.copyToClip(self.get_corrected_text())
            queueHandler.queueFunction(
                queueHandler.eventQueue, api.setFocusObject, self.parent
            )
            queueHandler.queueFunction(queueHandler.eventQueue, PASTE_GESTURE.send)
            queueHandler.queueFunction(
                queueHandler.eventQueue,
                play_sound,
                "text_replace"
            )
            queueHandler.queueFunction(
                queueHandler.eventQueue,
                speech.speakObject,
                self.parent,
                controlTypes.OutputReason.FOCUS,
            )
            if old_clipboard_text is not None:
                queueHandler.queueFunction(
                    queueHandler.eventQueue, api.copyToClip, old_clipboard_text
                )

