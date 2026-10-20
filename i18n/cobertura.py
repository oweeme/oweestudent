"""Qué parte de la interfaz está traducida a un idioma y qué falta (sirve sobre todo para Owee, cuyo
vocabulario crece con el glosario del idioma)."""
from i18n.catalogos import CATALOGOS
from i18n.catalogos.en import TEXTOS as INGLES


def informe(codigo: str) -> dict:
    """{'total', 'traducidos', 'faltan': [(español, inglés)]}, con lo más corto primero: las etiquetas
    cortas (botones, menús) son las que antes conviene tener en el idioma."""
    claves = list(INGLES)          # el inglés está siempre completo (lo garantizan las pruebas): es el universo de textos
    cat = CATALOGOS.get(codigo, {})
    faltan = [(k, _texto(INGLES.get(k, k))) for k in claves if k not in cat]
    faltan.sort(key=lambda p: (len(p[1]), p[1]))
    return {"total": len(claves), "traducidos": len(claves) - len(faltan), "faltan": faltan}


def _texto(v) -> str:
    return v[-1] if isinstance(v, tuple) else v


def como_tsv(faltan: list[tuple[str, str]]) -> str:
    """Lista para proponer palabras: inglés · español (el glosario de Owee usa esas dos columnas)."""
    return "en\tes\n" + "\n".join(f"{en}\t{es}" for es, en in faltan) + "\n"
