# coding: utf-8

# Copyright (c) 2021 Blind Pandas Team
# This file is covered by the GNU General Public License.

import sys
import os
import contextlib


PLUGIN_DIRECTORY = os.path.abspath(os.path.dirname(__file__))
LIBS_DIRECTORY = os.path.join(PLUGIN_DIRECTORY, "libs")
DATA_DIRECTORY = os.path.join(PLUGIN_DIRECTORY, "data")


@contextlib.contextmanager
def import_bundled_library():
    sys.path.insert(0, LIBS_DIRECTORY)
    try:
        yield
    finally:
        sys.path.remove(LIBS_DIRECTORY)
