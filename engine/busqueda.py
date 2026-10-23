"""Preguntar a tus documentos: búsqueda local (BM25) sobre tu material, tus notas y tus fichas de lectura, con citas.

Todo ocurre en tu equipo. El texto de cada página de tus archivos se guarda troceado en un índice local
(`indice.db`, junto a tu base: es un dato derivado, no se sincroniza). Una pregunta devuelve los pasajes más
relevantes con su fuente (documento y página). Si hay una IA configurada, redacta una respuesta usando SOLO esos
pasajes y citándolos como [1], [2]…; la respuesta se comprueba (citas que no existen se descartan) y los pasajes
siempre se muestran para verificar. Sin IA la búsqueda funciona igual.
"""
import math
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from i18n import t

MAX_PASAJE = 700         # caracteres por pasaje indexado (varios caben en el contexto de un modelo pequeño)
_PARADAS = set("""a al algo ante con contra cual cuando de del desde donde el ella ellas ello ellos en entre era es esa ese eso esta
este esto estos fue ha hay la las le les lo los mas me mi muy no nos o os otra otro para pero por que se si sin sobre su sus te
tu un una uno unos y ya the of and to in is are was were be been it its that this these those for on as at by an or from with which
what who how why when where does do did has have not but if than then also can may will would should could their there they
der die das und ist ein eine nicht mit von zu den dem des auf für im le la les des du un une et est que qui dans pour sur""".split())
_CJK = re.compile(r"[぀-ヿ㐀-䶿一-鿿]+")


def _sin_acentos(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def tokenizar(texto: str) -> list[str]:
    """Palabras normalizadas: sin acentos ni mayúsculas, sin palabras vacías, con una raíz simple (informar/información
    coinciden) y, para chino y japonés, pares de caracteres."""
    texto = _sin_acentos(texto).lower()
    out = []
    for m in re.finditer(r"[぀-ヿ㐀-䶿一-鿿]+|[a-z0-9]+", texto):
        w = m.group()
        if _CJK.fullmatch(w):
            out += [w] if len(w) == 1 else [w[i:i + 2] for i in range(len(w) - 1)]
            continue
        if w in _PARADAS or (len(w) < 2 and not w.isdigit()):
            continue
        if len(w) > 4 and w.endswith("es"):
            w = w[:-2]
        elif len(w) > 4 and w.endswith("s"):
            w = w[:-1]
        out.append(w[:6] if len(w) > 6 else w)
    return out


def trocear(texto: str, tam: int = MAX_PASAJE) -> list[str]:
    """Pasajes de una página: por párrafos, y las frases largas se cortan por oraciones."""
    pasajes, actual = [], ""
    for parrafo in re.split(r"\n\s*\n|\n(?=[A-ZÁÉÍÓÚ0-9•\-])", texto):
        for frase in re.split(r"(?<=[.!?。！？])\s+", parrafo.strip()) if len(parrafo) > tam else [parrafo.strip()]:
            if not frase:
                continue
            if actual and len(actual) + len(frase) > tam:
                pasajes.append(actual.strip())
                actual = ""
            actual += frase + " "
    if actual.strip():
        pasajes.append(actual.strip())
    return [p[:tam * 2] for p in pasajes if len(p) >= 20]


@dataclass
class Fuente:
    origen: str          # material · nota · lectura
    titulo: str
    pagina: int | None
    texto: str
    puntaje: float = 0.0
    plan_id: int | None = None
    ref_id: int | None = None    # id del material, de la nota o de la lectura

    def etiqueta(self) -> str:
        if self.origen == "material":
            return f"{self.titulo} · {t('p. {n}', n=self.pagina)}"
        return self.titulo


class Indice:
    """Índice local de las páginas de los archivos. Una entrada por contenido (hash), no por asignatura."""

    def __init__(self, ruta: str | Path):
        Path(ruta).parent.mkdir(parents=True, exist_ok=True)
        self.c = sqlite3.connect(str(ruta), check_same_thread=False)
        self.c.executescript("""
            CREATE TABLE IF NOT EXISTS docs (hash TEXT PRIMARY KEY, paginas INTEGER, hecho INTEGER DEFAULT 0);
            CREATE TABLE IF NOT EXISTS pasajes (id INTEGER PRIMARY KEY, hash TEXT, pagina INTEGER, texto TEXT, toks TEXT);
            CREATE INDEX IF NOT EXISTS idx_pasajes_hash ON pasajes(hash);""")

    def indexado(self, hash_: str) -> bool:
        r = self.c.execute("SELECT hecho FROM docs WHERE hash=?", (hash_,)).fetchone()
        return bool(r and r[0])

    def indexar_material(self, hash_: str, ruta: str, progreso=None) -> int:
        """Lee y trocea todas las páginas de un archivo. Devuelve cuántos pasajes guardó (0 si ya estaba)."""
        if self.indexado(hash_):
            return 0
        from engine import material
        total = material.num_paginas(ruta)
        self.c.execute("DELETE FROM pasajes WHERE hash=?", (hash_,))
        self.c.execute("INSERT OR REPLACE INTO docs(hash, paginas, hecho) VALUES (?,?,0)", (hash_, total))
        n = 0
        for pag in range(1, total + 1):
            texto = material.leer_pagina(ruta, pag)
            if texto.startswith("(Esta página no tiene texto"):
                texto = ""
            for p in trocear(texto):
                self.c.execute("INSERT INTO pasajes(hash, pagina, texto, toks) VALUES (?,?,?,?)",
                               (hash_, pag, p, " ".join(tokenizar(p))))
                n += 1
            if progreso and (pag % 5 == 0 or pag == total):
                progreso(pag / total)
        self.c.execute("UPDATE docs SET hecho=1 WHERE hash=?", (hash_,))
        self.c.commit()
        return n

    def olvidar(self, hash_: str):
        self.c.execute("DELETE FROM pasajes WHERE hash=?", (hash_,))
        self.c.execute("DELETE FROM docs WHERE hash=?", (hash_,))
        self.c.commit()

    def pasajes_de(self, hashes: list[str]):
        if not hashes:
            return []
        q = ",".join("?" * len(hashes))
        return self.c.execute(f"SELECT hash, pagina, texto, toks FROM pasajes WHERE hash IN ({q})", hashes).fetchall()


def _fuentes_vivas(conn, planes: list[int]) -> list[Fuente]:
    """Notas de material y fichas de lectura (poco texto y editables: se leen de la base cada vez, nunca quedan viejas)."""
    out = []
    q = ",".join("?" * len(planes))
    for r in conn.execute(f"""SELECT n.id, n.texto, n.pagina, n.tipo, m.titulo, m.id mid, m.plan_id FROM notas_material n
                              JOIN materiales m ON m.id=n.material_id WHERE m.plan_id IN ({q})""", planes):
        out.append(Fuente("nota", t("Tu nota en {titulo} (p. {n})", titulo=r["titulo"], n=r["pagina"]), r["pagina"], r["texto"],
                          plan_id=r["plan_id"], ref_id=r["mid"]))
    campos = ("pregunta", "metodo", "hallazgos", "limitaciones", "utilidad", "cita_clave", "notas")
    for r in conn.execute(f"SELECT * FROM lecturas WHERE plan_id IN ({q})", planes):
        from engine.biblio import citar
        cuerpo = "\n".join(f"{r[k].strip()}" for k in campos if (r[k] or "").strip())
        if cuerpo:
            out.append(Fuente("lectura", t("Tu ficha: {cita}", cita=citar(r)), None, cuerpo, plan_id=r["plan_id"], ref_id=r["id"]))
    return out


def materiales_pendientes(conn, indice: Indice, planes: list[int]) -> list:
    """Archivos de esos planes que están en este equipo y todavía no se han indexado (uno por contenido)."""
    q = ",".join("?" * len(planes))
    vistos, out = set(), []
    import os
    for m in conn.execute(f"SELECT * FROM materiales WHERE plan_id IN ({q}) AND hash IS NOT NULL ORDER BY id", planes):
        if m["tipo"] in ("imagen", "enlace") or m["hash"] in vistos or not m["ruta"] or not os.path.exists(m["ruta"]) or indice.indexado(m["hash"]):
            continue
        vistos.add(m["hash"])
        out.append(m)
    return out


def buscar(conn, indice: Indice, planes: list[int], pregunta: str, k: int = 5) -> list[Fuente]:
    """Los `k` pasajes más relevantes (BM25) de los planes dados, con su fuente."""
    consulta = list(dict.fromkeys(tokenizar(pregunta)))
    if not consulta or not planes:
        return []
    q = ",".join("?" * len(planes))
    mats = conn.execute(f"SELECT * FROM materiales WHERE plan_id IN ({q}) AND hash IS NOT NULL ORDER BY id", planes).fetchall()
    por_hash: dict[str, list] = {}
    for m in mats:
        por_hash.setdefault(m["hash"], []).append(m)
    docs: list[tuple[Fuente, list[str]]] = []
    for hash_, pagina, texto, toks in indice.pasajes_de(list(por_hash)):
        m = por_hash[hash_][0]
        docs.append((Fuente("material", m["titulo"], pagina, texto, plan_id=m["plan_id"], ref_id=m["id"]), toks.split()))
    for f in _fuentes_vivas(conn, planes):
        docs.append((f, tokenizar(f.texto)))
    if not docs:
        return []
    n = len(docs)
    largo_medio = sum(len(d[1]) for d in docs) / n or 1
    df: dict[str, int] = {}
    for _, toks in docs:
        for w in set(toks) & set(consulta):
            df[w] = df.get(w, 0) + 1
    k1, b = 1.5, 0.75
    puntuados = []
    for fuente, toks in docs:
        if not toks:
            continue
        frec: dict[str, int] = {}
        for w in toks:
            if w in df:
                frec[w] = frec.get(w, 0) + 1
        if not frec:
            continue
        s = 0.0
        for w, f in frec.items():
            idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
            s += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * len(toks) / largo_medio))
        s *= 1 + 0.15 * (len(frec) - 1)          # premia los pasajes que contienen varias palabras distintas de la pregunta
        puntuados.append((s, fuente))
    puntuados.sort(key=lambda p: -p[0])
    out, vistos = [], set()
    for s, f in puntuados:
        clave = (f.origen, f.ref_id, f.pagina, f.texto[:60])
        if clave in vistos:
            continue
        vistos.add(clave)
        f.puntaje = round(s, 3)
        out.append(f)
        if len(out) == k:
            break
    return out


# ---------- respuesta con citas ----------
_SISTEMA = ("Eres un asistente de estudio. Respondes SOLO con la información de los FRAGMENTOS numerados. "
            "Cada afirmación termina con la cita del fragmento que la respalda, como [1] o [2]. No uses conocimiento propio. "
            "Si los fragmentos no contienen la respuesta, responde exactamente: NO_ENCONTRADO. "
            "Responde en el mismo idioma de la pregunta, en pocas frases.")


def prompt_respuesta(pregunta: str, fuentes: list[Fuente], por_fragmento: int = 650) -> str:
    frag = "\n\n".join(f"[{i}] ({f.etiqueta()})\n{f.texto[:por_fragmento]}" for i, f in enumerate(fuentes, start=1))
    return f"FRAGMENTOS:\n{frag}\n\nPREGUNTA: {pregunta}\n\nRESPUESTA (con citas [n]):"


def revisar_respuesta(texto: str, n_fuentes: int) -> dict:
    """Comprueba la respuesta del modelo: quita citas que no existen y avisa si no cita nada o no encontró respuesta."""
    texto = texto.strip()
    if not texto or "NO_ENCONTRADO" in texto:
        return {"texto": "", "citas": [], "encontrada": False, "sin_citas": False}
    usadas = []

    def cita(m):
        i = int(m.group(1))
        if not 1 <= i <= n_fuentes:
            return ""                       # cita inventada: se quita
        if i not in usadas:
            usadas.append(i)
        return f" [{i}]"
    limpio = re.sub(r"\s*\[(\d+)\]", cita, texto)
    return {"texto": limpio.strip(), "citas": sorted(usadas), "encontrada": True, "sin_citas": not usadas}


def responder(pregunta: str, fuentes: list[Fuente], llm=None) -> dict:
    """Respuesta redactada por la IA con citas, ya comprobada. `llm` se puede inyectar (pruebas)."""
    if llm is None:
        from engine import ai
        llm = ai._llm
    crudo = llm(prompt_respuesta(pregunta, fuentes), _SISTEMA, 350)
    return revisar_respuesta(crudo, len(fuentes))


def con_citas(respuesta: dict, fuentes: list[Fuente]) -> str:
    """Texto para copiar: la respuesta y sus fuentes numeradas."""
    lineas = [respuesta["texto"], ""]
    for i in respuesta["citas"] or range(1, len(fuentes) + 1):
        f = fuentes[i - 1]
        lineas.append(f"[{i}] {f.etiqueta()}")
    return "\n".join(lineas).strip() + "\n"


def recorte(texto: str, pregunta: str, ancho: int = 320) -> str:
    """Trozo del pasaje alrededor de la primera palabra de la pregunta que aparece (para mostrar por qué salió)."""
    plano = _sin_acentos(texto).lower()
    pos = -1
    for w in re.findall(r"[a-z0-9]{3,}", _sin_acentos(pregunta).lower()):
        if w in _PARADAS:
            continue
        pos = plano.find(w[:6])
        if pos >= 0:
            break
    ini = max(0, pos - ancho // 3) if pos >= 0 else 0
    fin = min(len(texto), ini + ancho)
    return ("…" if ini else "") + texto[ini:fin].strip() + ("…" if fin < len(texto) else "")
