"""Tarjetas de estudio a partir de TUS apuntes, sin IA (para quien no tiene cuestionarios)."""
import re

_DEF = re.compile(r'^\s*(?:[*\-•]\s*)?\*{0,2}([^:\n—–*]{3,50}?)\*{0,2}\s*(?::|—|–| - )\s*(.{15,300})$')
_NEG = re.compile(r'\*\*([^*]{3,40})\*\*')


def desde_apuntes(texto: str, maximo: int = 30) -> list[tuple[str, str]]:
    """Devuelve [(pregunta, respuesta)]: definiciones «Término: explicación» y frases con **términos** en huecos."""
    out, vistos = [], set()

    def add(p, r):
        if p not in vistos:
            vistos.add(p)
            out.append((p, r))

    for linea in texto.splitlines():
        l = linea.strip()
        m = _DEF.match(l)
        if m and len(m.group(1).split()) <= 6 and not m.group(1).lower().startswith(("http", "tarea")):
            add(f"¿Qué es / qué significa «{m.group(1).strip()}»?", m.group(2).strip())
            continue
        for term in _NEG.findall(l):
            hueco = l.replace(f"**{term}**", "_____").replace("**", "")
            if len(hueco) > 25 and "_____" in hueco:
                add(f"Completa: {hueco.strip('*- ')}", term)
    return out[:maximo]
