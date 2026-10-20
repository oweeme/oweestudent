"""Tarjetas de estudio a partir de TUS apuntes, sin IA (para quien no tiene cuestionarios).

Tipos: definiciones («Término: explicación»), huecos con **negritas** o con {{llaves}} (una tarjeta por hueco, como los
«cloze» de Anki), huecos automáticos sobre las palabras clave del texto, y tarjetas de PRODUCCIÓN: en el repaso escribes
la respuesta en vez de solo reconocerla.
"""
import difflib
import re
import unicodedata

_DEF = re.compile(r'^\s*(?:[*\-•]\s*)?\*{0,2}([^:\n—–*]{3,50}?)\*{0,2}\s*(?::|—|–| - )\s*(.{15,300})$')
_NEG = re.compile(r'\*\*([^*]{3,40})\*\*')
_LLAVES = re.compile(r'\{\{([^{}]{2,60})\}\}')


def desde_apuntes(texto: str, maximo: int = 30) -> list[tuple[str, str]]:
    """Devuelve [(pregunta, respuesta)]: definiciones «Término: explicación» y frases con **términos** en huecos."""
    out, vistos = [], set()

    def add(p, r):
        if p not in vistos:
            vistos.add(p)
            out.append((p, r))

    for linea in texto.splitlines():
        l = linea.strip()
        if _LLAVES.search(l):
            for p, r in cloze(l):
                add(p, r)
            continue
        m = _DEF.match(l)
        if m and len(m.group(1).split()) <= 6 and not m.group(1).lower().startswith(("http", "tarea")):
            add(f"¿Qué es / qué significa «{m.group(1).strip()}»?", m.group(2).strip())
            continue
        for term in _NEG.findall(l):
            hueco = l.replace(f"**{term}**", "_____").replace("**", "")
            if len(hueco) > 25 and "_____" in hueco:
                add(f"Completa: {hueco.strip('*- ')}", term)
    return out[:maximo]


def cloze(texto: str, maximo: int = 40) -> list[tuple[str, str]]:
    """Una tarjeta por cada {{hueco}}: «La {{fotosíntesis}} ocurre en los {{cloroplastos}}» da dos tarjetas, cada una
    con un solo hueco (los demás se ven) y como respuesta la palabra tapada."""
    out = []
    for frase in re.split(r"(?<=[.!?])\s+|\n", texto):
        marcas = list(_LLAVES.finditer(frase))
        for i, m in enumerate(marcas):
            partes, previo = [], 0
            for j, otra in enumerate(marcas):
                partes.append(frase[previo:otra.start()])
                partes.append("_____" if i == j else otra.group(1))
                previo = otra.end()
            partes.append(frase[previo:])
            hueco = "".join(partes).strip(" *-•")
            if len(hueco) > 12:
                out.append((f"Completa: {hueco}", m.group(1).strip()))
    return out[:maximo]


def huecos_automaticos(texto: str, maximo: int = 12) -> list[tuple[str, str]]:
    """Tapa en cada frase la palabra clave del texto que contenga (la más característica). Sin IA ni marcas:
    sirve para apuntes que ya están escritos. Revisa las tarjetas: una palabra clave no siempre es la mejor pregunta."""
    from engine.practica import terminos_clave
    claves = terminos_clave(texto, 20)
    out, vistos = [], set()
    for frase in re.split(r"(?<=[.!?])\s+|\n", texto):
        f = frase.strip(" *-•\t")
        if not 40 <= len(f) <= 220:
            continue
        for palabra in claves:
            m = re.search(rf"(?<!\w){re.escape(palabra)}(?!\w)", f, re.IGNORECASE)
            if m:
                pregunta = f"Completa: {f[:m.start()]}_____{f[m.end():]}"
                if pregunta not in vistos:
                    vistos.add(pregunta)
                    out.append((pregunta, m.group(0)))
                break
    return out[:maximo]


def _normalizar(s: str) -> str:
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]", "", s.lower()).split())


def comparar(escrita: str, correcta: str) -> dict:
    """¿Coincide lo que escribiste con la respuesta? Ignora mayúsculas, acentos y puntuación. `casi` = una o dos letras de
    diferencia (una errata). Las marcas de glifo de Owee (`[owee]suna`) se comparan por su romanización."""
    from engine.practica import plano
    a, b = _normalizar(plano(escrita)) or "", _normalizar(plano(correcta)) or ""
    if not a:
        return {"correcta": False, "casi": False, "similitud": 0.0}
    exacta = a == b
    sim = difflib.SequenceMatcher(None, a, b).ratio()
    return {"correcta": exacta, "casi": (not exacta) and sim >= 0.8 and abs(len(a) - len(b)) <= 2, "similitud": round(sim, 2)}


def sugerencia_de_nota(resultado: dict) -> int:
    """Nota de repaso (0-5) que corresponde a lo escrito: acierto 4, errata 3, fallo 1."""
    return 4 if resultado["correcta"] else 3 if resultado["casi"] else 1
