"""Un PDF pierde los # y las viñetas del Markdown: aquí se reconstruyen a partir de las palabras clave del plan
(SEMESTRE, Módulo N:, Idiomas - Fase, Temas Clave:, Bibliografía Principal:, Caso de Estudio…) para que se lea como el .md.
Si el texto no tiene al menos dos módulos, se devuelve tal cual."""
import re

_MESES = re.compile(r'Meses?\s+\d+\s*[-–]\s*\d+', re.I)
_SEM = re.compile(r'^\W*SEMESTRE\s+\d', re.I)
_MOD = re.compile(r'^\W*M[óo]dulo\s+\d+\s*:', re.I)
_IDI = re.compile(r'^\W*Idiomas\s*[-–]\s*Fase', re.I)
_META = re.compile(r'^(Modalidad|Duración Total|Dedicación|Plataformas[^:]*):\s*(.+)$', re.I)
_SIN_ADORNO = re.compile(r'^\W+')
_FIN_ITEM = re.compile(r'[.;?!]$')
_DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes")
_IDIOMAS = re.compile(r'\s(?=(?:Inglés|Alemán|Chino Mandarín|Francés|Portugués|Italiano|Japonés|Ruso):)')


def _limpia(s: str) -> str:
    return _SIN_ADORNO.sub('', s).strip()


def _juntar_titulo(lineas, i):
    """Un título puede ocupar 2-3 líneas; termina donde aparece «(Meses a - b)». Devuelve (texto, siguiente índice)."""
    partes = [lineas[i]]
    while not _MESES.search(" ".join(partes)) and len(partes) < 4 and i + len(partes) < len(lineas):
        partes.append(lineas[i + len(partes)])
    if not _MESES.search(" ".join(partes)):
        return lineas[i], i + 1
    return " ".join(partes), i + len(partes)


def _cronograma(lineas):
    cab = next((l for l in lineas if re.match(r'^Día\s+Bloque 1', l)), None)
    if not cab or 'Bloque 2' not in cab:
        return []
    b1, b2 = re.sub(r'^Día\s+', '', cab).split('Bloque 2', 1)
    filas = ["| Día | " + b1.strip() + " | Bloque 2" + b2.strip() + " |", "| --- | --- | --- |"]
    for l in lineas:
        dia = next((d for d in _DIAS if l.startswith(d + " ")), None)
        if dia:
            partes = _IDIOMAS.split(l[len(dia):].strip(), maxsplit=1)
            if len(partes) == 2:
                filas.append(f"| {dia} | {partes[0].strip()} | {partes[1].strip()} |")
    return filas if len(filas) > 2 else []


def _items(bloque, nuevo):
    """Agrupa líneas partidas por el ancho de la página en elementos completos."""
    out = []
    for l in bloque:
        if out and not nuevo(out[-1], l):
            out[-1] += " " + l
        else:
            out.append(l)
    return out


def a_markdown(texto: str) -> str:
    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    if sum(1 for l in lineas if _MOD.match(l)) < 2:
        return texto
    out, i, seccion, bloque = [], 0, None, []

    def volcar():
        nonlocal bloque
        if not bloque:
            return
        if seccion == "temas":
            out.extend(f"  * {x}" for x in _items(bloque, lambda prev, l: bool(_FIN_ITEM.search(prev))))
        elif seccion == "libros":
            for x in _items(bloque, lambda prev, l: bool(_FIN_ITEM.search(prev))):
                a, sep, b = x.partition(" – ")
                out.append(f"  * *{a.strip()}* – {b.strip()}" if sep else f"  * {x}")
        elif seccion == "idioma":
            out.extend(f"  * {x}" for x in _items(bloque, lambda prev, l: bool(re.match(r'^(Recursos|Tarea semanal|Objetivo)\s*:', l))))
        else:
            out.extend(f"  * {x}" for x in bloque)
        bloque = []

    out += _cronograma(lineas) + [""]
    titulo = []
    while i < len(lineas) and not _META.match(lineas[i]) and not _SEM.match(lineas[i]) and not _MOD.match(lineas[i]):
        l = lineas[i]
        if l.startswith("🎓") or titulo:
            titulo.append(_limpia(l))
        i += 1
    if titulo:
        out = ["# " + " ".join(titulo), ""] + out
    while i < len(lineas):
        l = lineas[i]
        m = _META.match(l)
        if m and not out[-1:] == ["__unidad__"]:
            if seccion is None:
                out.append(f"**{m.group(1)}:** {m.group(2)}")
                i += 1
                continue
        if _SEM.match(l):
            volcar(); seccion = None
            txt, i = _juntar_titulo(lineas, i)
            out += ["", "## " + txt]
            continue
        if _MOD.match(l) or _IDI.match(l):
            volcar(); seccion = "idioma" if _IDI.match(l) else None
            txt, i = _juntar_titulo(lineas, i)
            out += ["", ("### 🌐 " if _IDI.match(l) else "### 🔹 ") + _limpia(txt)]
            continue
        etiqueta = re.match(r'^(Temas Clave|Bibliografía Principal|Opciones y Dónde[^:]*|Caso de Estudio[^:]*):\s*(.*)$', _limpia(l))
        if etiqueta:
            volcar()
            k = etiqueta.group(1)
            seccion = ("temas" if k.startswith("Temas") else "libros" if k.startswith("Bibliograf") else
                       "opciones" if k.startswith("Opciones") else "entregable")
            out.append(f"* **{'📝 ' if seccion == 'entregable' else ''}{k}:**")
            i += 1
            continue
        if seccion == "idioma" and re.search(r'\(Objetivo[^)]*\):$', l):
            volcar()
            out.append(f"* **{l}**")
            i += 1
            continue
        op = re.match(r'^(Opciones de Búsqueda|Alternativas[^:]*):\s*(.*)$', l)
        if seccion == "opciones" and op:
            volcar()
            bloque = [f"**{op.group(1)}:** {op.group(2)}"]
            i += 1
            while i < len(lineas) and not re.match(r'^(Alternativas[^:]*:|\W*Caso de Estudio|\W*M[óo]dulo|\W*SEMESTRE|\W*Idiomas)', lineas[i]):
                bloque[0] += " " + lineas[i]
                i += 1
            volcar()
            continue
        if seccion == "entregable":
            e = re.match(r'^Entregable:\s*(.*)$', l)
            if e:
                bloque = [f"*Entregable:* {e.group(1)}"]
                i += 1
                while i < len(lineas) and not re.match(r'^(\W*M[óo]dulo|\W*SEMESTRE|\W*Idiomas)', lineas[i]):
                    bloque[0] += " " + lineas[i]
                    i += 1
                volcar()
                continue
        bloque.append(l)
        i += 1
    volcar()
    return "\n".join(out)
