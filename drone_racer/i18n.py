import os.path
import gettext

def translations(domain):
    locales_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
    locales_dir = os.path.join(locales_dir, 'resources', 'locales')
    # We do want NullTranslations instance for unsupported languages
    translation = gettext.translation(domain, locales_dir, fallback=True)
    return translation.gettext, translation.ngettext

