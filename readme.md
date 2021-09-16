# Information

- authors: Fawaz Abdulrahman<fawaz.ar94@gmail.com> & Musharraf Omer<ibnomer2011@hotmail.com>
- version: 1.1
- download

## functionality

the purpose of the addon is to find and correct the spelling errors quickly in a written text; additionally, you can create a list of words called personal dictionary; the words in which will be added to the suggestions list of the misspelled words.


## usage

- select some text using the normal selection keys, such as Control + a for selecting all.
- press NVDA+Alt+s to invoke the addon interface.
- the spellcheck will be done based on your current keyboard input.
- alternatively, you can pick a language manually by pressing NVDA+ALT+SHIFT+L.
- if there are no errors, a message will be announced indicating that there are no spelling mistakes.
- in case there are errors, use right and left arrows to navigate among the misspelled words, and enter or down arrow to bring up the suggestion menu. 
- navigate among the suggestions with up and down arrow, then enter to pick a suggestion. The NVDA will announce the chosen suggestion for each error while navigating among them with left and right arrows. 
- while navigating among the errors with right and left arrows, you can press backspace to remove a chosen suggestion.
- when done, press Control + r to replace the chosen suggestions in the selected text.
- in addition to replacing the words, control+r also adds the word to the personal dictionary if you had picked that option.

### personal dictionary

in the suggestions' menu, there is an option to add the word to the personal dictionary. The next time you look for a similar misspelling word, the personal dictionary words will appear in the suggestions list in addition to the normal dictionary.
For instance, if you added the word "Fawaz" to the personal dictionary, the next time if you typed "Fawz", "Fawaz" would be among the given suggestions.
You can remove any word that has been added to the personal dictionary by editing the file (language tag).dic which can be found in the spellcheck_dic folder in the user configuration folder of the NVDA. 
That is for the installed version appdata/roaming/nvda and for the portable version user config folder.
the file name for the US English would be en_US.dic.

### Ignore for this session

The option before last in the suggestion menu is ignore for this session. So if there is a word which raises a spelling error, and you want it to be left out from being spellchecked, you can use this choice (Ignore for this session).
for example: if the text was "hello users of nvda, we hope you are having a wonderful time with nvda and its add-ons. Unquestionably, nvda is an amazing screen reader.", if you added nvda to ignore for this session, the number of errors will reduce from 4 to one, the remaining one would be "addons". In other words, all "nvda" will be removed from the list of errors for that session.


## Support for Other languages

The addon comes with the English dictionary by default, which will be installed with your permission while installing the addon.
The spell check will be done depending on the keyboard input language. However, if the dictionary hasn't been installed previously, NVDA will prompt you to install the dictionary of that language. Once you click yes, the dictionary will be installed, and you can spellcheck in that language now on.
Additionally, you can press NVDA+ALT+SHIFT+L to bring up a list of languages where you can select a language manually and download the dictionary if it hasn't been downloaded previously or perform spell check in that language. press the same shortcut once more to return to the previous method, which is checking based on the keyboard input.


## notes

- closing the addon interface with the escape key will discard all the changes; nothing will be saved.
- even if you only want to add words to the personal dictionary without replacing any text, you must press control+r for these words to be added to the personal dictionary.
- you can change the launching addon hotkey (NVDA+alt+s), executing the action hotkey (control+r), and manual language selection hotkey (NVDA+Alt+SHIFT+L) from the input gestures dialog.


## keyboard hotkeys

- NVDA+alt+s to activate the addon. (Can be changed from the input gestures).
- right and left arrows to navigate between the words with spelling errors.
- enter or down-arrow to bring up the suggestion’s menu. 
- up and down arrow to navigate between suggestions. 
- enter to choose a suggestion.
- backspace to remove a chosen suggestion.
- control + c to copy the corrected text to the clipboard without replacing the selected text. (Can be changed from input gestures).
- control + r to replace the selected suggestions in the text field. (Can be changed from input gestures).
- escape to close both the suggestions menu and misspelled words menu.
- NVDA+Alt+SHIFT+L to select a language manually (can be changed from input gestures).
