"""Traducción de la interfaz.

El texto original en español es la clave: `t("Guardar")`. El español no necesita catálogo;
los demás idiomas son diccionarios `{español: traducción}` en `i18n/catalogos/<código>.py`.
Si falta una traducción se prueba la cadena de respaldo (p. ej. ruso → inglés) y, al final, el español.

    t("Hola {nombre}", nombre="Ana")
    DIAS = [marcar("Lunes")]; t(DIAS[0])     # textos que se eligen luego: se declaran con marcar()
    tn(n, "{n} tarjeta", "{n} tarjetas")      # clave del catálogo = la forma plural; valor = tupla de formas
"""
import locale
import os

from i18n.catalogos import CATALOGOS

IDIOMA_BASE = "es"
# código -> nombre en su propio idioma (así se reconoce aunque la interfaz esté en otro)
NOMBRES = {"es": "Español", "en": "English", "de": "Deutsch", "ru": "Русский",
           "zh": "中文", "ja": "日本語", "qow": "Owee"}
# idioma -> idiomas a probar, en orden, cuando falta una traducción
RESPALDO = {"qow": ("en",), "de": ("en",), "ru": ("en",), "zh": ("en",), "ja": ("en",), "en": ()}

_actual = IDIOMA_BASE


def disponibles() -> list[str]:
    """Idiomas con catálogo (más el español), en el orden de NOMBRES."""
    return [c for c in NOMBRES if c == IDIOMA_BASE or CATALOGOS.get(c)]


def idioma() -> str:
    return _actual


def fijar_idioma(codigo: str) -> str:
    """Cambia el idioma de la interfaz; si no existe usa el español. Devuelve el código aplicado."""
    global _actual
    _actual = codigo if codigo in disponibles() else IDIOMA_BASE
    return _actual


def detectar_sistema() -> str:
    """Idioma del sistema si lo tenemos traducido; si no, el español."""
    for var in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        v = os.environ.get(var, "")
        if v:
            return _normalizar(v.split(":")[0])
    try:
        return _normalizar(locale.getlocale()[0] or "")
    except (ValueError, TypeError):
        return IDIOMA_BASE


def _normalizar(valor: str) -> str:
    cod = valor.replace("-", "_").split("_")[0].split(".")[0].lower()
    return cod if cod in disponibles() else IDIOMA_BASE


def iniciar() -> str:
    """Aplica el idioma guardado en la configuración, o el del sistema la primera vez."""
    from engine import ai
    return fijar_idioma(ai.cargar_config().get("idioma") or detectar_sistema())


def indice_plural(codigo: str, n: int) -> int:
    """Qué forma plural usa cada idioma (0 = singular). Ruso: tres formas; chino, japonés y Owee: una."""
    if codigo in ("zh", "ja", "qow"):
        return 0
    if codigo == "ru":
        n = abs(int(n))
        if n % 10 == 1 and n % 100 != 11:
            return 0
        return 1 if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14 else 2
    return 0 if n == 1 else 1


def _buscar(clave: str):
    for cod in (_actual, *RESPALDO.get(_actual, ())):
        v = CATALOGOS.get(cod, {}).get(clave)
        if v:
            return cod, v
    return IDIOMA_BASE, None


def _dar_formato(texto: str, kw: dict) -> str:
    if not kw:
        return texto
    try:
        return texto.format(**kw)
    except (KeyError, IndexError, ValueError):
        return texto


def marcar(texto: str) -> str:
    """No traduce: señala un texto que se traducirá más tarde con t(variable) (listas, tablas). Devuelve el mismo texto."""
    return texto


def t(texto: str, **kw) -> str:
    """Traduce `texto` (en español) al idioma actual y rellena las {variables}."""
    cod, v = _buscar(texto)
    return _dar_formato(v if isinstance(v, str) else texto, kw)


def tn(n, uno: str, otros: str, **kw) -> str:
    """Texto con plural: `uno` y `otros` son las dos formas en español; `n` se puede usar como {n}."""
    kw.setdefault("n", n)
    cod, v = _buscar(otros)
    if isinstance(v, (tuple, list)):
        formas = v
    else:
        formas, cod = (uno, otros), IDIOMA_BASE
    return _dar_formato(formas[min(indice_plural(cod, n), len(formas) - 1)], kw)
