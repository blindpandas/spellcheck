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
import os
import api
import controlTypes
import eventHandler
import globalPluginHandler
import speech
from contextlib import suppress
from NVDAObjects import NVDAObject
from scriptHandler import script
from logHandler import log
from enchant .checker import SpellChecker
from scriptHandler import script
from textInfos import POSITION_SELECTION

def getSelectedText() -> str:
	"""Retrieve the selected text.
	If the selected text is missing - extract the text from the clipboard.
	@return: selected text, text from the clipboard, or an empty string
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
	if not info or info.isCollapsed:
		try:
			text = api.getClipData()
		except Exception:
			text = ''
		if not text or not isinstance(text, str):
			return ''
		return text
	return info.text


# This should be set to Tru in the final release 
# It prevent any key strokes from reaching the application
# Thereby avoiding any unintentional edits to the underlying text control
CAPTURE_KEYS_WHILE_IN_FOCUS = False


class KeyboardNavigableNVDAObjectMixin:
    windowClassName = ""
    windowControlID = 0

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Save this here
        self.original_misspelling = self.name
        self._accepted_suggestion = None

    def get_replacement_info(self):
        return (
            self.original_misspelling,
            self._accepted_suggestion or self.original_misspelling,
        )

    def on_suggestion_accepted(self, suggestion):
        self._accepted_suggestion = suggestion
        self.description = f"accepted: {suggestion}"
        self.back_to_misspelling()

    def back_to_misspelling(self):
        eventHandler.queueEvent("suggestionsClosed", self.parent.parent)
        eventHandler.queueEvent("gainFocus", self.parent)

    @property
    def suggestions_menu(self):
        suggestions = SpellChecker.suggest(erWord)
        self._suggestions_menu = MenuObject(name="Suggestions")
        self._suggestions_menu.init_container_state(
            items=[
                SuggestionMenuItemObject(
                    acceptance_callback=self.on_suggestion_accepted,
                    parent=self._suggestions_menu,
                    name=item,
                )
                for item in suggestions
            ],
            on_top_edge=self.back_to_misspelling,
        )
        return self._suggestions_menu

    @script(gesture="kb:backspace")
    def script_backspace(self, gesture):
        """Reject suggestion"""
        if self._accepted_suggestion is not None:
            self._accepted_suggestion = None
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


class SuggestionMenuItemObject(MenuItemObject):
    def __init__(self, acceptance_callback, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.acceptance_callback = acceptance_callback

    @script(gesture="kb:downarrow")
    def script_downarrow(self, gesture):
        self.go_to_next()

    @script(gesture="kb:uparrow")
    def script_uparrow(self, gesture):
        self.go_to_prev()

    @script(gesture="kb:enter")
    def script_accept_suggestion(self, gesture):
        self.acceptance_callback(self.name)


class MenuObject(KeyboardNavigableNVDAObjectMixin, ItemContainerMixin, NVDAObject):
    role = controlTypes.ROLE_MENU

    def __init__(self, name, *args, items=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name
        self.parent = api.getFocusObject()
        self.processID = self.parent.processID
        self.init_container_state(
            items=[MisspellingMenuItemObject(parent=self, name=item) for item in items]
        )

    def close_menu(self):
        eventHandler.queueEvent("gainFocus", self.parent)

    def event_gainFocus(self):
        speech.speakObject(self, controlTypes.OutputReason.FOCUS)
        eventHandler.queueEvent("gainFocus", self.get_current_item())


class SpellCheckMenu(MenuObject):
    """This is a special menu object."""

    def get_misspellings_and_suggestions(self):
        return {
            misspelling: replacement
            for (misspelling, replacement) in (
                item.get_replacement_info() for item in self
            )
        }

    def close_menu(self):
        # Implement any text replacement logic here
        # There are two possible options:
        # 1. NVDA builtin way: not sure!
        # 2. As an exercise, try exploring win32 api docs to find a function: also not sure
        # If found, the native function could then be called using the ctypes.windll module
        log.info(self.get_misspellings_and_suggestions())
        super().close_menu()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    @script(gesture="kb:nvda+z")
    def script_launch_testing(self, gesture):
        chk = SpellChecker("en_US")
        chk.set_text(getSelectedText())
        current_focus = api.getFocusObject()
        if not current_focus.states.intersection(
            {controlTypes.STATE_EDITABLE, controlTypes.STATE_MULTILINE}
        ):
            return
        # Create our fake menu object
        misspellingsMenu = SpellCheckMenu(
            name="Spelling Errors",
            items=[err.word for err in chk]
            )
        # Let NVDA set focus to the fake object
        # NVDA does not care what object you give it, as long as it is an NVDAObject
        # It could even be my late grandmothre for that matter
        eventHandler.queueEvent("gainFocus", misspellingsMenu)
