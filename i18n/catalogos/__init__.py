"""Catálogos de traducción {texto en español: traducción}. Se importan de forma estática para que
PyInstaller y `flet build` los incluyan. Un idioma sin archivo simplemente no aparece."""
CATALOGOS: dict[str, dict] = {}

try:
    from i18n.catalogos.en import TEXTOS as _en
    CATALOGOS["en"] = _en
except ImportError:
    pass
try:
    from i18n.catalogos.de import TEXTOS as _de
    CATALOGOS["de"] = _de
except ImportError:
    pass
try:
    from i18n.catalogos.ru import TEXTOS as _ru
    CATALOGOS["ru"] = _ru
except ImportError:
    pass
try:
    from i18n.catalogos.zh import TEXTOS as _zh
    CATALOGOS["zh"] = _zh
except ImportError:
    pass
try:
    from i18n.catalogos.qow import TEXTOS as _qow
    CATALOGOS["qow"] = _qow
except ImportError:
    pass
try:
    from i18n.catalogos.ja import TEXTOS as _ja
    CATALOGOS["ja"] = _ja
except ImportError:
    pass
