# coding: utf-8

# Copyright (c) 2021 Blind Pandas Team
# This file is covered by the GNU General Public License.


import os
import zipfile
import wx
import gui
import globalVars
import contextlib


HERE = os.path.abspath(os.path.dirname(__file__))
BUNDLED_LANGUAGE_DICTIONARIES_ARCHIVE = os.path.join(HERE, "bundled_dictionaries.zip")
SPELLCHECK_DICTIONARIES_DIRECTORY = os.path.join(globalVars.appArgs.configPath, "spellcheck_dictionaries")


import addonHandler
addonHandler.initTranslation()


def onInstall():
    if os.path.isdir(SPELLCHECK_DICTIONARIES_DIRECTORY):
        return
    os.mkdir(SPELLCHECK_DICTIONARIES_DIRECTORY)
    rv = gui.messageBox(
        _("The Spellcheck add-on comes bundled with some default language dictionaries. Would you like to add them?"),
        _("Add Default Dictionaries"),
        wx.YES_NO|wx.ICON_INFORMATION
    )
    if rv == wx.YES:
        with zipfile.ZipFile(BUNDLED_LANGUAGE_DICTIONARIES_ARCHIVE, "r") as archive:
            archive.extractall(SPELLCHECK_DICTIONARIES_DIRECTORY)
        with contextlib.suppress(Exception):
            os.unlink(BUNDLED_LANGUAGE_DICTIONARIES_ARCHIVE)

