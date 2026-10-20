"""BibTeX: leer y escribir referencias, y fichas de lectura en Markdown. Sin dependencias ni red."""
import re
import unicodedata

_ACENTOS = {"'": "\u0301", "`": "\u0300", '"': "\u0308", "^": "\u0302", "~": "\u0303", "c": "\u0327", "v": "\u030c"}
_ESPECIALES = {r"\ss": "ß", r"\ae": "æ", r"\AE": "Æ", r"\o": "ø", r"\O": "Ø", r"\aa": "å", r"\&": "&", r"\%": "%",
               r"\_": "_", r"\#": "#", r"\$": "$", r"\i": "i"}
_ENTRADA = re.compile(r"@\s*(\w+)\s*([{(])", re.S)


def _latex_a_unicode(s: str) -> str:
    for k, v in _ESPECIALES.items():
        s = s.replace(k, v)
    s = re.sub(r"\\([\'`\"^~cv])\s*\{\s*(\\?[A-Za-z])\s*\}", lambda m: _acentuar(m.group(1), m.group(2)), s)
    s = re.sub(r"\{\\([\'`\"^~])\s*([A-Za-z])\}", lambda m: _acentuar(m.group(1), m.group(2)), s)
    s = re.sub(r"\\([\'`\"^~])\s*([A-Za-z])", lambda m: _acentuar(m.group(1), m.group(2)), s)
    return s


def _acentuar(marca: str, letra: str) -> str:
    return unicodedata.normalize("NFC", letra.lstrip("\\") + _ACENTOS[marca])


def _limpiar(valor: str) -> str:
    v = _latex_a_unicode(valor)
    v = v.replace("{", "").replace("}", "").replace("\\", "")
    return re.sub(r"\s+", " ", v).strip()


def _leer_valor(s: str, i: int) -> tuple[str, int]:
    """Valor de un campo BibTeX desde la posición i: {…} con llaves anidadas, "…" o palabra suelta."""
    while i < len(s) and s[i].isspace():
        i += 1
    if i >= len(s):
        return "", i
    if s[i] == "{":
        nivel, j = 1, i + 1
        while j < len(s) and nivel:
            nivel += (s[j] == "{") - (s[j] == "}")
            j += 1
        return s[i + 1:j - 1], j
    if s[i] == '"':
        j = i + 1
        while j < len(s) and not (s[j] == '"' and s[j - 1] != "\\"):
            j += 1
        return s[i + 1:j], j + 1
    j = i
    while j < len(s) and s[j] not in ",}\n":
        j += 1
    return s[i:j].strip(), j


def leer_bibtex(texto: str) -> list[dict]:
    """Referencias del texto BibTeX: [{tipo, clave, titulo, autores, anio, fuente, doi, url}]. Ignora @comment/@string."""
    out, pos = [], 0
    while True:
        m = _ENTRADA.search(texto, pos)
        if not m:
            return out
        tipo = m.group(1).lower()
        cierre = "}" if m.group(2) == "{" else ")"
        i = m.end()
        if tipo in ("comment", "string", "preamble"):
            nivel, j = 1, i
            while j < len(texto) and nivel:
                nivel += (texto[j] == m.group(2)) - (texto[j] == cierre)
                j += 1
            pos = j
            continue
        coma = texto.find(",", i)
        if coma < 0:
            return out
        clave = texto[i:coma].strip()
        campos, j = {}, coma + 1
        while j < len(texto):
            while j < len(texto) and (texto[j].isspace() or texto[j] == ","):
                j += 1
            if j >= len(texto) or texto[j] == cierre:
                j += 1
                break
            k = j
            while j < len(texto) and texto[j] not in "=,}":
                j += 1
            nombre = texto[k:j].strip().lower()
            if j >= len(texto) or texto[j] != "=":
                continue
            valor, j = _leer_valor(texto, j + 1)
            campos[nombre] = _limpiar(valor)
        pos = j
        autores = [a.strip() for a in re.split(r"\s+and\s+", campos.get("author", "") or campos.get("editor", "")) if a.strip()]
        anio = re.search(r"\d{4}", campos.get("year", "") or campos.get("date", ""))
        if campos.get("title"):
            out.append({"tipo": tipo, "clave": clave, "titulo": campos["title"], "autores": "; ".join(autores),
                        "anio": int(anio.group()) if anio else None,
                        "fuente": campos.get("journal") or campos.get("booktitle") or campos.get("publisher") or "",
                        "doi": campos.get("doi", ""), "url": campos.get("url", "")})


def _ascii(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower())


def clave_para(r: dict, usadas: set[str]) -> str:
    """Clave BibTeX estable: apellido + año + primera palabra del título (con sufijo si ya existe)."""
    primero = (r.get("autores") or "").split(";")[0].split(",")[0].strip()
    palabra = next((w for w in re.split(r"\W+", r.get("titulo") or "") if len(w) > 3), "")
    base = _ascii(primero) + str(r.get("anio") or "") + _ascii(palabra)[:12] or "ref"
    c, n = base, 2
    while c in usadas:
        c, n = f"{base}{n}", n + 1
    usadas.add(c)
    return c


def _esc(v: str) -> str:
    return v.replace("\\", " ").replace("{", "(").replace("}", ")").replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


def a_bibtex(lecturas: list) -> str:
    """BibTeX de las lecturas (filas con titulo, autores, anio, fuente, doi, url, tipo_bib, clave_bib)."""
    usadas, partes = set(), []
    for r in lecturas:
        r = dict(r)
        clave = r.get("clave_bib") if r.get("clave_bib") and r["clave_bib"] not in usadas else clave_para(r, usadas)
        usadas.add(clave)
        campos = [("author", " and ".join(a.strip() for a in (r.get("autores") or "").split(";") if a.strip())),
                  ("title", "{" + _esc(r["titulo"]) + "}"), ("year", str(r["anio"]) if r.get("anio") else ""),
                  ("journal" if (r.get("tipo_bib") or "article") == "article" else "publisher", r.get("fuente") or ""),
                  ("doi", r.get("doi") or ""), ("url", r.get("url") or "")]
        cuerpo = ",\n".join(f"  {k} = {{{_esc(v) if k != 'title' else v}}}" for k, v in campos if v)
        partes.append(f"@{r.get('tipo_bib') or 'article'}{{{clave},\n{cuerpo}\n}}")
    return "\n\n".join(partes) + ("\n" if partes else "")


_ETIQUETAS_FICHA = (("pregunta", "Pregunta de investigación"), ("metodo", "Método"), ("hallazgos", "Hallazgos"),
                    ("limitaciones", "Limitaciones"), ("utilidad", "Cómo me sirve"), ("cita_clave", "Cita clave"),
                    ("notas", "Notas"))


def citar(r) -> str:
    """Referencia corta: «Apellido et al. (2020). Título»."""
    r = dict(r)
    autores = [a.split(",")[0].strip() for a in (r.get("autores") or "").split(";") if a.strip()]
    quien = "" if not autores else autores[0] if len(autores) == 1 else f"{autores[0]} y {autores[1]}" if len(autores) == 2 \
        else f"{autores[0]} et al."
    anio = f" ({r['anio']})" if r.get("anio") else ""
    return (f"{quien}{anio}. " if quien or anio else "") + r["titulo"]


def fichas_markdown(lecturas: list, etiquetas: dict | None = None) -> str:
    """Fichas en Markdown, una por lectura (solo los campos con contenido). `etiquetas` traduce los nombres de campo."""
    etiquetas = etiquetas or {}
    bloques = []
    for r in lecturas:
        r = dict(r)
        lineas = [f"## {citar(r)}"]
        if r.get("fuente"):
            lineas.append(f"*{r['fuente']}*")
        if r.get("doi"):
            lineas.append(f"DOI: {r['doi']}")
        for k, nombre in _ETIQUETAS_FICHA:
            if (r.get(k) or "").strip():
                lineas.append(f"\n**{etiquetas.get(k, nombre)}:** {r[k].strip()}")
        bloques.append("\n".join(lineas))
    return "\n\n".join(bloques) + ("\n" if bloques else "")
