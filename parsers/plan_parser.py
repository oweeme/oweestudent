"""Convierte un plan de estudios en Markdown (como el del Máster) en estructura.

Estructura esperada (flexible):
  ## SEMESTRE ...               -> semestre
  ### 🔹 Módulo N: Título (Meses a - b)
     * **Temas Clave:** / **Bibliografía Principal:** / **Opciones ...** /
       **📝 Caso de Estudio Práctico (Tarea N):**  con sub-viñetas
  ### 🌐 Idiomas - Fase N (Meses ...)
     * **Inglés (Objetivo ...):**  con sub-viñetas *Recursos:* / *Tarea semanal:*
  | tabla de cronograma semanal |
Si el archivo no sigue esa forma, cae a un modo genérico (encabezados -> unidades).
"""
import re

_MESES = re.compile(r'\(?\s*Meses?\s+(\d+)\s*[-–]\s*(\d+)\s*\)?', re.I)
_BOLD_KEY = re.compile(r'^\*\s+\*\*(.+?)\*\*\s*(.*)$')
_SUB = re.compile(r'^(\s+)[*-]\s+(.*)$')
_LIBRO = re.compile(r'^\*(.+?)\*\s*[–—-]\s*(.+)$')
_EMOJI = re.compile(r'^[^\w\[\(]+', re.U)


def _limpia(s: str) -> str:
    s = re.sub(r'\*\*|__', '', s)
    return _EMOJI.sub('', s.strip()).strip(' :')


def _cortar_meses(titulo: str):
    m = _MESES.search(titulo)
    if not m:
        return titulo.strip(), None, None
    return _MESES.sub('', titulo).strip(' -–'), int(m.group(1)), int(m.group(2))


def _tabla(lineas):
    filas = []
    for l in lineas:
        if not l.strip().startswith('|'):
            continue
        celdas = [c.strip() for c in l.strip().strip('|').split('|')]
        if all(re.fullmatch(r':?-{2,}:?', c) for c in celdas):
            continue
        filas.append(celdas)
    return filas


def parse_plan(texto: str) -> dict:
    lineas = texto.splitlines()
    plan = {"titulo": "", "meta": {}, "cronograma": [], "unidades": [], "guia": []}
    semestre = None
    unidad = None
    seccion = None      # clave de la sección de viñetas actual
    idioma = None       # sub-sección de idioma actual
    en_guia = False
    tabla_buf = []

    for raw in lineas:
        l = raw.rstrip()
        if l.startswith('# ') and not plan["titulo"]:
            plan["titulo"] = _limpia(l[2:])
            continue
        if l.strip().startswith('|'):
            tabla_buf.append(l)
            continue
        if l.startswith('## '):
            h = _limpia(l[3:])
            en_guia = 'GUÍA' in h.upper() or 'GUIA' in h.upper()
            if en_guia:
                unidad = None
                plan["guia"].append({"titulo": h, "items": []})
            elif 'CRONOGRAMA' not in h.upper():
                semestre = _cortar_meses(h)[0]
            seccion = idioma = None
            continue
        if l.startswith('### '):
            en_guia = False
            titulo, m1, m2 = _cortar_meses(_limpia(l[4:]))
            es_idioma = l[4:].strip().startswith('🌐') or titulo.lower().startswith('idiomas')
            unidad = {
                "titulo": titulo, "semestre": semestre, "mes_ini": m1, "mes_fin": m2,
                "tipo": "idioma" if es_idioma else "modulo",
                "temas": [], "libros": [], "busqueda": [], "alternativas": [],
                "entregable": None, "idiomas": [],
            }
            plan["unidades"].append(unidad)
            seccion = idioma = None
            continue
        if l.startswith('---') or not l.strip():
            continue

        # metadatos de cabecera (**Clave:** valor)
        if unidad is None and not en_guia:
            m = re.match(r'^\*\*(.+?):\*\*\s*(.+?)\s*$', l)
            if m:
                plan["meta"][m.group(1).strip()] = m.group(2).strip()
            continue

        if en_guia:
            plan["guia"][-1]["items"].append(l.strip())
            continue

        m = _BOLD_KEY.match(l)
        if m:
            clave, resto = _limpia(m.group(1)), m.group(2).strip()
            k = clave.lower()
            if unidad["tipo"] == "idioma":
                idioma = {"nombre": clave, "detalles": []}
                unidad["idiomas"].append(idioma)
                seccion = "idioma"
            else:
                seccion = ("temas" if k.startswith("temas") else
                           "libros" if k.startswith("bibliograf") else
                           "opciones" if k.startswith("opciones") else
                           "entregable" if "caso de estudio" in k else None)
                if seccion == "entregable":
                    unidad["entregable"] = {"titulo": clave, "descripcion": ""}
            if resto:
                _agregar(unidad, seccion, idioma, resto)
            continue

        s = _SUB.match(l)
        if s and seccion:
            _agregar(unidad, seccion, idioma, s.group(2).strip())

    plan["cronograma"] = _cronograma(_tabla(tabla_buf))
    if not plan["unidades"]:
        plan["unidades"] = _generico(lineas)
    return plan


def _agregar(unidad, seccion, idioma, txt):
    txt = txt if seccion in ("libros", "opciones") else txt.replace('*', '')
    if seccion == "temas":
        unidad["temas"].append(_limpia(txt))
    elif seccion == "libros":
        m = _LIBRO.match(txt)
        unidad["libros"].append({"titulo": m.group(1).strip(), "autor": m.group(2).strip()}
                                if m else {"titulo": _limpia(txt), "autor": ""})
    elif seccion == "opciones":
        clave, _, valor = txt.partition(':')
        clave = _limpia(clave).lower()
        valor = valor.replace('**', '').strip() or txt
        destino = "busqueda" if "búsqueda" in clave or "busqueda" in clave else "alternativas"
        unidad[destino].append(valor.strip())
    elif seccion == "entregable" and unidad["entregable"]:
        d = unidad["entregable"]
        d["descripcion"] = (d["descripcion"] + " " + re.sub(r'^\*?Entregable:\*?\s*', '', txt)).strip()
    elif seccion == "idioma" and idioma is not None:
        idioma["detalles"].append(re.sub(r'\*', '', txt).strip())


def _cronograma(filas):
    if len(filas) < 2:
        return []
    cab = [_limpia(c) for c in filas[0]]
    return [{"dia": _limpia(f[0]),
             "bloques": {cab[i]: _limpia(f[i]) for i in range(1, min(len(f), len(cab)))}}
            for f in filas[1:] if f]


def _generico(lineas):
    """Modo genérico: cada encabezado (#) es una unidad y sus viñetas/líneas, temas."""
    unidades, actual = [], None
    for l in lineas:
        h = re.match(r'^#{1,4}\s+(.*)', l)
        if h:
            actual = {"titulo": _limpia(h.group(1)), "semestre": None, "mes_ini": None,
                      "mes_fin": None, "tipo": "modulo", "temas": [], "libros": [],
                      "busqueda": [], "alternativas": [], "entregable": None, "idiomas": []}
            unidades.append(actual)
        elif actual and len(l.strip()) > 3 and not l.strip().startswith(('|', '---')):
            actual["temas"].append(_limpia(re.sub(r'^\s*[*\-\d.]+\s*', '', l)))
    unidades = [u for u in unidades if u["temas"]]
    if not unidades:  # texto plano sin encabezados: una sola unidad con cada línea como tema
        temas = [_limpia(re.sub(r'^\s*[*\-\d.]+\s*', '', l)) for l in lineas if len(l.strip()) > 3]
        if temas:
            unidades = [{"titulo": "Contenido importado", "semestre": None, "mes_ini": None,
                         "mes_fin": None, "tipo": "modulo", "temas": temas, "libros": [],
                         "busqueda": [], "alternativas": [], "entregable": None, "idiomas": []}]
    return unidades
