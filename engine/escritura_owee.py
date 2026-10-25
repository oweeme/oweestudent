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


# ---------- valorar un texto escrito en Owee (sin IA: reglas del idioma + léxico aprobado) ----------
import functools
import re
from pathlib import Path

_PALABRA = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*")
_VOCABULARIO = Path(__file__).resolve().parents[1] / "i18n" / "datos" / "owee_vocabulario.txt"


@functools.lru_cache(maxsize=1)
def conocidas() -> frozenset[str]:
    """Palabras aprobadas: léxico del curso + vocabulario del idioma (y las partes de los compuestos)."""
    base = {w.lower() for w in curso.LEXICO}
    try:
        base |= {l.strip().lower() for l in _VOCABULARIO.read_text(encoding="utf-8").splitlines() if l.strip()}
    except OSError:
        pass
    return frozenset(base | {p for w in base for p in w.split("-")})


@functools.lru_cache(maxsize=1)
def _nivel_de() -> dict[str, int]:
    """Palabra → nivel del curso (0-3) donde aparece por primera vez."""
    out: dict[str, int] = {}
    for l in curso.lecciones():
        for w in curso.palabras_de(l["md"]):
            for p in w.lower().split("-"):
                out.setdefault(p, l["nivel"])
    return out


def valorar(texto: str) -> dict:
    """Qué tal está escrito: palabras imposibles en Owee, palabras fuera del léxico, nombres, variedad y nivel del vocabulario."""
    sabidas, niveles = conocidas(), _nivel_de()
    invalidas, desconocidas, validas, nombres, nivel = [], [], [], 0, None
    for tok in _PALABRA.findall(texto or ""):
        partes = tok.lower().split("-")
        if not all(owee.valida(p) for p in partes):
            if tok[0].isupper():
                nombres += 1                       # un nombre propio puede traer letras que Owee no usa
            elif tok not in invalidas:
                invalidas.append(tok)
            continue
        if tok[0].isupper() and tok.lower() not in sabidas:
            nombres += 1
            continue
        validas.append(tok.lower())
        if all(p in sabidas for p in partes):
            nivel = max([nivel or 0] + [niveles[p] for p in partes if p in niveles])
        elif tok.lower() not in desconocidas:
            desconocidas.append(tok.lower())
    oraciones = len([x for x in re.split(r"[.!?\n]+", texto or "") if _PALABRA.search(x)])
    total = len(validas)
    conocidas_n = sum(1 for w in validas if all(p in sabidas for p in w.split("-")))
    return {"palabras": total, "distintas": len(set(validas)), "oraciones": oraciones, "nombres": nombres,
            "invalidas": invalidas, "desconocidas": desconocidas,
            "cobertura": conocidas_n / total if total else 0.0, "variedad": len(set(validas)) / total if total else 0.0,
            "nivel": nivel, "palabras_por_oracion": total / oraciones if oraciones else 0.0}


# ---------- diccionario y palabra del día ----------
import unicodedata
from datetime import date


def _sin_tildes(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def clases() -> list[str]:
    return sorted({v[1] for v in curso.LEXICO.values() if v[1]})


def buscar(consulta: str = "", clase: str | None = None, limite: int = 60) -> tuple[list[tuple[str, str, str]], int]:
    """(palabra, significado, clase) que coinciden con la consulta en Owee o en español, y cuántas hay en total.
    Primero la palabra exacta, luego las que empiezan por la consulta, luego las que la contienen."""
    q = _sin_tildes((consulta or "").strip())
    filas = []
    for w, (sig, cl) in curso.LEXICO.items():
        if clase and cl != clase:
            continue
        if not q:
            rango = 3
        else:
            ws, ss = _sin_tildes(w), _sin_tildes(sig)
            if ws == q or q in [x.strip() for x in ss.replace("/", ",").split(",")]:
                rango = 0
            elif ws.startswith(q) or ss.startswith(q):
                rango = 1
            elif q in ws or q in ss:
                rango = 2
            else:
                continue
        filas.append((rango, len(w), w, sig, cl))
    filas.sort()
    return [(w, s, c) for _, _, w, s, c in filas[:limite]], len(filas)


def palabra_del_dia(hoy: date | None = None, hasta: str | None = None) -> tuple[str, str] | None:
    """Una palabra distinta cada día (la misma para todos ese día), de las que ya puedes haber visto en el curso."""
    pool = palabras(hasta) or palabras()
    if not pool:
        return None
    return pool[(hoy or date.today()).toordinal() % len(pool)]
