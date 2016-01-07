import os.path
import gettext

def translations(domain):
    locales_dir = os.path.abspath(os.path.dirname(__file__))
    translation = gettext.translation(domain, locales_dir)
    return translation.gettext, translation.ngettext

