"""Práctica de ESCRIBIR en Owee Script: palabras del curso, rondas y comprobación. Sin interfaz."""
import random

from i18n import owee
from owee_curso import curso


def palabras(hasta: str | None = None) -> list[tuple[str, str]]:
    """(palabra, significado) de las lecciones hasta `hasta` (incluida; None = todas). Solo palabras con significado
    y escribibles en Owee: la app no inventa palabras."""
    vistos, out = set(), []
    for l in curso.lecciones():
        for w in curso.palabras_de(l["md"]):
            s = curso.significado(w)
            if s and w not in vistos and owee.valida(w.replace("-", "")):
                vistos.add(w)
                out.append((w, s))
        if hasta and l["id"] == hasta:
            break
    return out


MODOS = ("es_a_owee", "glifo_a_owee", "glifo_a_romano")      # escribir lo que significa · copiar el glifo · leer el glifo


def ronda(pool: list[tuple[str, str]], n: int = 5, rng: random.Random | None = None) -> list[dict]:
    rng = rng or random.Random()
    elegidas = rng.sample(pool, min(n, len(pool)))
    return [{"palabra": w, "significado": s, "modo": MODOS[i % len(MODOS)]} for i, (w, s) in enumerate(elegidas)]


def normalizar(texto: str) -> str:
    return "".join(ch for ch in (texto or "").lower() if ch.isalpha())


def comprobar(respuesta: str, palabra: str) -> bool:
    """Compara sin importar mayúsculas, espacios ni guiones («sade-kelo» = «sadekelo»)."""
    return normalizar(respuesta) == normalizar(palabra)


def teclas() -> dict:
    """Las teclas del teclado de sílabas: vocales, una fila por consonante y dígitos."""
    return {"vocales": list(owee.VOCALES),
            "silabas": [[c + v for v in owee.VOCALES] for c in owee.CONSONANTES],
            "digitos": [str(d) for d in range(10)]}
