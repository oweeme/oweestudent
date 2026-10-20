"""Convierte el Markdown de una lección del curso de Owee en bloques que la pantalla sabe dibujar.

Bloques: {"t": "md", "texto"} · {"t": "owee", "lineas", "traduccion"} · {"t": "vocab", "palabras"} ·
{"t": "tabla", "cab", "filas"} · {"t": "resp", "md"} · {"t": "titulo", "texto"}.
"""
import re

_NUM = re.compile(r"\[\[([^\]]+)\]\]")
_VOCAB = re.compile(r"<!--\s*vocabulario\s+(.*?)-->", re.S)


def _fila(linea: str) -> list[str]:
    return [c.strip() for c in linea.strip().strip("|").split("|")]


def _es_separador(linea: str) -> bool:
    return bool(re.fullmatch(r"\|?[\s:\-|]+\|?", linea.strip())) and "-" in linea


def parsear(md: str) -> list[dict]:
    lineas = md.splitlines()
    bloques: list[dict] = []
    parrafo: list[str] = []
    i = 0

    def vaciar():
        if parrafo:
            texto = _NUM.sub(lambda m: f"`{m.group(1)}`", "\n".join(parrafo)).strip()
            parrafo.clear()
            if not texto:
                return
            if (bloques and bloques[-1]["t"] == "owee" and not bloques[-1]["traduccion"]
                    and re.fullmatch(r"\*[^*].*[^*]\*", texto, re.S)):     # «*traducción*» justo debajo de un bloque owee
                bloques[-1]["traduccion"] = texto.strip("*").strip()
            else:
                bloques.append({"t": "md", "texto": texto})

    while i < len(lineas):
        l = lineas[i]
        s = l.strip()
        if s.startswith("```owee"):
            vaciar()
            i += 1
            cuerpo = []
            while i < len(lineas) and not lineas[i].strip().startswith("```"):
                if lineas[i].strip():
                    cuerpo.append(lineas[i].strip())
                i += 1
            bloques.append({"t": "owee", "lineas": cuerpo, "traduccion": ""})
        elif s.startswith("<!--vocabulario"):
            vaciar()
            m = _VOCAB.search(s)
            if m:
                bloques.append({"t": "vocab", "palabras": m.group(1).split()})
        elif s == "<!--resp-->":
            vaciar()
            i += 1
            cuerpo = []
            while i < len(lineas) and lineas[i].strip() != "<!--/resp-->":
                cuerpo.append(lineas[i])
                i += 1
            bloques.append({"t": "resp", "md": _NUM.sub(lambda m: f"`{m.group(1)}`", "\n".join(cuerpo)).strip()})
        elif s.startswith("|"):
            vaciar()
            filas = []
            while i < len(lineas) and lineas[i].strip().startswith("|"):
                if not _es_separador(lineas[i]):
                    filas.append(_fila(lineas[i]))
                i += 1
            i -= 1
            if filas:
                bloques.append({"t": "tabla", "cab": filas[0], "filas": filas[1:]})
        elif s.startswith("#"):
            vaciar()
            bloques.append({"t": "titulo", "texto": s.lstrip("#").strip()})
        elif not s:
            vaciar()
        else:
            parrafo.append(l)
        i += 1
    vaciar()
    return bloques


def palabras_de(md: str) -> list[str]:
    """Vocabulario declarado en la lección (sin repetir, en orden)."""
    vistas: list[str] = []
    for m in _VOCAB.finditer(md):
        for w in m.group(1).split():
            if w.lower() not in vistas:
                vistas.append(w.lower())
    return vistas


def limpiar_celda(celda: str) -> str:
    """Texto plano de una celda de tabla (sin ** ni `)."""
    return re.sub(r"[*`]", "", celda).strip()
