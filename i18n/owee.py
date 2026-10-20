"""Owee romano <-> Owee Script. Adaptado de `herramientas/owee_script.py` del proyecto Owee
(https://github.com/oweeme/owee, MIT). Mismas reglas que owee.js y el teclado Fcitx5.

    a_escritura("sade-kelo Ana") -> glifos U+E000..E049, nexo U+E03C y marca de nombre U+E03D
    a_romano(texto_script)       -> romano
    valida("kelo")               -> True si es Owee válido (sílabas V o CV, sin «i»)

Una palabra imposible se deja en romano: no se pierde texto. El texto se guarda SIEMPRE en romano; los
glifos (área de uso privado de Unicode) solo se usan para mostrar.
"""
import re

VOCALES = "aeou"
CONSONANTES = ["p", "b", "t", "d", "k", "g", "f", "s", "m", "n", "l", "r", "sh", "ch"]
NEXO, NOMBRE = chr(0xE03C), chr(0xE03D)
RANGO_PUA = (0xE000, 0xE049)

_POR_ROMANO: dict[str, str] = {}
_cp = 0xE000
for _v in VOCALES:
    _POR_ROMANO[_v] = chr(_cp)
    _cp += 1
for _c in CONSONANTES:
    for _v in VOCALES:
        _POR_ROMANO[_c + _v] = chr(_cp)
        _cp += 1
_POR_GLIFO = {v: k for k, v in _POR_ROMANO.items()}
_POR_GLIFO[NEXO] = "-"
for _d in range(10):
    _POR_GLIFO[chr(0xE040 + _d)] = str(_d)
_SILABA = re.compile(r"(sh|ch|[pbtdkgfsmnlr])?([aeou])")
_MARCADOR = re.compile(r"\{[^{}]*\}")      # {variable}: no se convierte
_TOKEN = re.compile(r"[A-Za-z]+(?:-[A-Za-z]+)*|[0-9]")


def silabas(palabra: str) -> list[str] | None:
    w = palabra.lower()
    out = [(m.group(1) or "") + m.group(2) for m in _SILABA.finditer(w)]
    return out if out and "".join(out) == w else None


def valida(palabra: str) -> bool:
    return silabas(palabra) is not None


def _palabra(p: str) -> str | None:
    s = silabas(p)
    return "".join(_POR_ROMANO[x] for x in s) if s else None


def a_escritura(texto: str, digitos: bool = True) -> str:
    def tok(m):
        t = m.group(0)
        if t.isdigit():
            return chr(0xE040 + int(t)) if digitos else t
        partes = t.split("-")
        conv = [_palabra(p) for p in partes]
        nombre = bool(re.fullmatch(r"[A-Z][a-z]*", partes[0]))
        if all(c is not None for c in conv):
            out = NEXO.join(conv)
        else:
            out = "-".join(c if c is not None else p for c, p in zip(conv, partes))
        return (NOMBRE if nombre and conv[0] is not None else "") + out
    return _TOKEN.sub(tok, texto)


def a_escritura_con_marcadores(plantilla: str) -> str:
    """Convierte una plantilla con {variables}: solo el texto de alrededor; los marcadores quedan intactos
    (si no, «{fecha}» se leería como la palabra owee «fe-cha»)."""
    partes, previo = [], 0
    for m in _MARCADOR.finditer(plantilla):
        partes.append(a_escritura(plantilla[previo:m.start()]))
        partes.append(m.group(0))
        previo = m.end()
    partes.append(a_escritura(plantilla[previo:]))
    return "".join(partes)


def a_romano(texto: str) -> str:
    out, mayuscula = "", False
    for ch in texto:
        if ch == NOMBRE:
            mayuscula = True
            continue
        r = _POR_GLIFO.get(ch, ch)
        if mayuscula and ch in _POR_GLIFO:
            r = r[:1].upper() + r[1:]
            mayuscula = False
        out += r
    return out


def tiene_glifos(texto: str) -> bool:
    return any(RANGO_PUA[0] <= ord(c) <= RANGO_PUA[1] for c in texto)
