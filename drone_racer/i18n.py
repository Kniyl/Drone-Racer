"""Tiny wrapper around gettext tailored for this software.
"""

import os.path
import gettext

def translations(domain):
    """Create translation functions from the given domain.mo files. These
    files are searched for in <directory_of_i18n.py>/../resources/locales/

    Returns a couple of functions: the first one to translate strings and
    the second one to translate pluralized strings.
    """
    locales_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    locales_dir = os.path.join(locales_dir, 'resources', 'locales')
    # We do want NullTranslations instance for unsupported languages
    translation = gettext.translation(domain, locales_dir, fallback=True)
    return translation.gettext, translation.ngettext

