"""Catálogos de traducción {texto en español: traducción}. Se importan de forma estática para que
PyInstaller y `flet build` los incluyan. Un idioma sin archivo simplemente no aparece."""
CATALOGOS: dict[str, dict] = {}

try:
    from i18n.catalogos.en import TEXTOS as _en
    CATALOGOS["en"] = _en
except ImportError:
    pass
