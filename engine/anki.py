"""Exportar tus tarjetas a Anki: paquete `.apkg` (con tu progreso de repaso si quieres) o texto CSV/TSV.

El `.apkg` es el formato de colección de Anki (esquema 11, que Anki de escritorio, AnkiDroid y AnkiMobile
importan). Cada tarjeta lleva una marca estable (guid) derivada de su identidad en OweeStudent: si exportas otra vez
y vuelves a importar, Anki actualiza las notas en lugar de duplicarlas. Las tarjetas de Owee con glifos incluyen la
fuente Owee Sans dentro del paquete para que se vean igual en Anki.
"""
import csv
import hashlib
import html
import io
import json
import re
import sqlite3
import tempfile
import time
import zipfile
from datetime import date, datetime, time as hora, timedelta
from pathlib import Path

from i18n import owee

RAIZ = Path(__file__).resolve().parents[1]
FUENTE = RAIZ / "assets/fonts/OweeSans.ttf"
NOMBRE_FUENTE = "_OweeSans.ttf"            # el guion bajo inicial: Anki no la borra como «medio sin usar»
MODELO_ID, MAZO_BASE_ID = 1735689601001, 1735689602000
_B91 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!#$%&()*+,-./:;<=>?@[]^_`{|}~"
CSS = """.card { font-family: arial; font-size: 20px; text-align: center; color: black; background-color: white; }
@font-face { font-family: "Owee Sans"; src: url("_OweeSans.ttf"); }
.owee { font-family: "Owee Sans"; font-size: 56px; line-height: 1.2; }
small { color: #777; }"""


# ---------- contenido de las tarjetas ----------
def a_html(texto: str) -> str:
    """HTML del campo: texto escapado; las marcas de glifo (`[glifo]ka`, `[owee]suna`) pasan a la fuente Owee."""
    for marca, con_romano in (("[glifo]", False), ("[owee]", True)):
        if texto.startswith(marca):
            romano = texto[len(marca):]
            h = f'<span class="owee">{html.escape(owee.a_escritura(romano))}</span>'
            return h + (f"<br><small>{html.escape(romano)}</small>" if con_romano else "")
    return html.escape(texto).replace("\n", "<br>")


def a_texto(texto: str) -> str:
    """Texto plano para CSV: las marcas de glifo pasan a su romanización (el CSV no lleva fuentes)."""
    for marca in ("[glifo]", "[owee]"):
        if texto.startswith(marca):
            return texto[len(marca):]
    return texto


def _etiqueta(s: str) -> str:
    return re.sub(r"\s+", "_", s.strip()).replace("::", "_") or "sin_nombre"


def tarjetas_a_exportar(conn, perfil_id: int, plan_id: int | None = None, tema_id: int | None = None):
    sql = """SELECT k.*, t.titulo tema, p.titulo plan, p.id plan_id FROM tarjetas k JOIN temas t ON t.id=k.tema_id
             JOIN unidades u ON u.id=t.unidad_id JOIN planes p ON p.id=u.plan_id WHERE p.perfil_id=?"""
    args: list = [perfil_id]
    if tema_id:
        sql, args = sql + " AND k.tema_id=?", args + [tema_id]
    elif plan_id:
        sql, args = sql + " AND p.id=?", args + [plan_id]
    return conn.execute(sql + " ORDER BY p.id, t.id, k.id", args).fetchall()


# ---------- CSV ----------
def a_csv(tarjetas, separador: str = "\t") -> str:
    """Texto para «Archivo → Importar» de Anki: frente, reverso y etiquetas (asignatura, tema)."""
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=separador, lineterminator="\n")
    for k in tarjetas:
        w.writerow([a_texto(k["pregunta"]), a_texto(k["respuesta"]), f"{_etiqueta(k['plan'])} {_etiqueta(k['tema'])}"])
    return buf.getvalue()


# ---------- .apkg ----------
def _base91(n: int) -> str:
    out = ""
    while n:
        n, r = divmod(n, len(_B91))
        out = _B91[r] + out
    return out or _B91[0]


def _guid(clave: str) -> str:
    return _base91(int.from_bytes(hashlib.sha256(clave.encode()).digest()[:8], "big"))


def _csum(campo: str) -> int:
    limpio = re.sub(r"<[^>]*>", "", campo)
    return int(hashlib.sha1(limpio.encode("utf-8")).hexdigest()[:8], 16)


def _modelo(ahora: int) -> dict:
    return {str(MODELO_ID): {
        "id": MODELO_ID, "name": "OweeStudent: Básico", "type": 0, "mod": ahora, "usn": -1, "sortf": 0, "did": 1,
        "tmpls": [{"name": "Tarjeta 1", "ord": 0, "qfmt": "{{Frente}}", "afmt": "{{FrontSide}}<hr id=answer>{{Reverso}}",
                   "bqfmt": "", "bafmt": "", "did": None, "bfont": "", "bsize": 0}],
        "flds": [{"name": "Frente", "ord": 0, "sticky": False, "rtl": False, "font": "Arial", "size": 20, "media": []},
                 {"name": "Reverso", "ord": 1, "sticky": False, "rtl": False, "font": "Arial", "size": 20, "media": []}],
        "css": CSS, "latexPre": "\\documentclass[12pt]{article}\n\\special{papersize=3in,5in}\n\\usepackage[utf8]{inputenc}\n"
                                "\\usepackage{amssymb,amsmath}\n\\pagestyle{empty}\n\\setlength{\\parindent}{0in}\n\\begin{document}\n",
        "latexPost": "\\end{document}", "req": [[0, "any", [0]]], "tags": [], "vers": []}}


def _mazo(did: int, nombre: str, ahora: int) -> dict:
    return {"id": did, "name": nombre, "mod": ahora, "usn": -1, "lrnToday": [0, 0], "revToday": [0, 0], "newToday": [0, 0],
            "timeToday": [0, 0], "collapsed": False, "desc": "", "dyn": 0, "conf": 1, "extendedRev": 50, "extendedNew": 10}


_ESQUEMA = """
CREATE TABLE col (id integer primary key, crt integer not null, mod integer not null, scm integer not null, ver integer not null,
  dty integer not null, usn integer not null, ls integer not null, conf text not null, models text not null, decks text not null,
  dconf text not null, tags text not null);
CREATE TABLE notes (id integer primary key, guid text not null, mid integer not null, mod integer not null, usn integer not null,
  tags text not null, flds text not null, sfld integer not null, csum integer not null, flags integer not null, data text not null);
CREATE TABLE cards (id integer primary key, nid integer not null, did integer not null, ord integer not null, mod integer not null,
  usn integer not null, type integer not null, queue integer not null, due integer not null, ivl integer not null, factor integer not null,
  reps integer not null, lapses integer not null, left integer not null, odue integer not null, odid integer not null,
  flags integer not null, data text not null);
CREATE TABLE revlog (id integer primary key, cid integer not null, usn integer not null, ease integer not null, ivl integer not null,
  lastIvl integer not null, factor integer not null, time integer not null, type integer not null);
CREATE TABLE graves (usn integer not null, oid integer not null, type integer not null);
CREATE INDEX ix_notes_usn on notes (usn); CREATE INDEX ix_cards_usn on cards (usn); CREATE INDEX ix_revlog_usn on revlog (usn);
CREATE INDEX ix_cards_nid on cards (nid); CREATE INDEX ix_cards_sched on cards (did, queue, due);
CREATE INDEX ix_revlog_cid on revlog (cid); CREATE INDEX ix_notes_csum on notes (csum);
"""


def crear_apkg(tarjetas, destino: str | Path, con_progreso: bool = True, hoy: date | None = None) -> dict:
    """Escribe el paquete `.apkg`. Un mazo por asignatura (`OweeStudent::Asignatura`). Con `con_progreso`, las tarjetas que
    ya repasaste llegan a Anki como tarjetas de repaso con su intervalo y fecha; el resto, como nuevas.
    Devuelve {tarjetas, mazos, con_fuente}."""
    tarjetas = list(tarjetas)
    hoy = hoy or date.today()
    ahora = int(time.time())
    # el «día 0» de la colección queda 400 días atrás: las fechas de repaso son días desde ahí
    crt = int(datetime.combine(hoy - timedelta(days=400), hora(4, 0)).timestamp())
    mazos: dict[int, int] = {}
    usa_fuente = False
    with tempfile.TemporaryDirectory() as d:
        bd = Path(d) / "collection.anki2"
        c = sqlite3.connect(bd)
        c.executescript(_ESQUEMA)
        decks = {"1": _mazo(1, "Default", ahora)}
        for k in tarjetas:
            if k["plan_id"] not in mazos:
                did = MAZO_BASE_ID + k["plan_id"]
                mazos[k["plan_id"]] = did
                decks[str(did)] = _mazo(did, f"OweeStudent::{k['plan'].replace('::', ' ')}", ahora)
        nid = cid = ahora * 1000
        for k in tarjetas:
            nid += 1
            cid += 1
            frente, reverso = a_html(k["pregunta"]), a_html(k["respuesta"])
            usa_fuente = usa_fuente or "class=\"owee\"" in frente or "class=\"owee\"" in reverso
            clave = k["uid"] if "uid" in k.keys() and k["uid"] else f"id-{k['id']}"
            etiquetas = f" {_etiqueta(k['plan'])} {_etiqueta(k['tema'])} "
            c.execute("INSERT INTO notes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                      (nid, _guid(clave), MODELO_ID, ahora, -1, etiquetas, f"{frente}\x1f{reverso}", frente, _csum(frente), 0, ""))
            repasada = con_progreso and (k["repeticiones"] or 0) > 0 and k["proximo_repaso"]
            if repasada:
                dias = (date.fromisoformat(k["proximo_repaso"]) - (hoy - timedelta(days=400))).days
                c.execute("INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (cid, nid, mazos[k["plan_id"]], 0, ahora, -1, 2, 2, dias, max(1, k["intervalo_dias"] or 1), 2500,
                           k["repeticiones"], 0, 0, 0, 0, 0, ""))
            else:
                c.execute("INSERT INTO cards VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                          (cid, nid, mazos[k["plan_id"]], 0, ahora, -1, 0, 0, nid % 1000000, 0, 0, 0, 0, 0, 0, 0, 0, ""))
        conf = {"nextPos": len(tarjetas) + 1, "estTimes": True, "activeDecks": [1], "sortType": "noteFld", "timeLim": 0,
                "sortBackwards": False, "addToCur": True, "curDeck": 1, "newBury": True, "newSpread": 0, "dueCounts": True,
                "curModel": str(MODELO_ID), "collapseTime": 1200}
        dconf = {"1": {"id": 1, "name": "Default", "replayq": True, "lapse": {"leechFails": 8, "minInt": 1, "delays": [10],
                       "leechAction": 0, "mult": 0}, "rev": {"perDay": 200, "fuzz": 0.05, "ivlFct": 1, "maxIvl": 36500, "ease4": 1.3,
                       "bury": True, "minSpace": 1}, "timer": 0, "maxTaken": 60, "usn": 0, "new": {"perDay": 20, "delays": [1, 10],
                       "separate": True, "ints": [1, 4, 7], "initialFactor": 2500, "bury": True, "order": 1}, "mod": 0,
                       "autoplay": True}}
        c.execute("INSERT INTO col VALUES (1,?,?,?,11,0,0,0,?,?,?,?,?)",
                  (crt, ahora, ahora * 1000, json.dumps(conf), json.dumps(_modelo(ahora)), json.dumps(decks), json.dumps(dconf), "{}"))
        c.commit()
        c.close()
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(bd, "collection.anki2")
            if usa_fuente and FUENTE.exists():
                z.write(FUENTE, "0")
                z.writestr("media", json.dumps({"0": NOMBRE_FUENTE}))
            else:
                z.writestr("media", "{}")
    return {"tarjetas": len(tarjetas), "mazos": len(mazos), "con_fuente": bool(usa_fuente and FUENTE.exists())}
