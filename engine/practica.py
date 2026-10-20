"""Práctica activa: recuperación libre, explicar con tus palabras (Feynman) y simulacros.

Leer y subrayar da sensación de saber; lo que fija el recuerdo es intentar recordar sin mirar (recuperación),
explicar con palabras sencillas (Feynman) y examinarse con el reloj (simulacro). Todo funciona sin IA; si hay una IA
configurada, además compara tu respuesta con tu material y señala huecos, siempre usando SOLO el texto de referencia.
"""
import json
import random
import re
from dataclasses import dataclass

from engine.busqueda import tokenizar

TIPOS = ("recuperacion", "feynman", "simulacro")
_FRASE = re.compile(r"(?<=[.!?。！？])\s+")


# ---------- palabras clave y cobertura (sin IA) ----------
def terminos_clave(texto: str, n: int = 12) -> list[str]:
    """Las palabras más características de la referencia (las que repite y no son comunes), tal como están escritas."""
    cuenta: dict[str, int] = {}
    forma: dict[str, dict[str, int]] = {}
    for m in re.finditer(r"[^\W\d_]{4,}", texto, re.UNICODE):
        palabra = m.group()
        raiz = tokenizar(palabra)
        if not raiz:
            continue
        r = raiz[0]
        cuenta[r] = cuenta.get(r, 0) + 1
        forma.setdefault(r, {})
        forma[r][palabra.lower()] = forma[r].get(palabra.lower(), 0) + 1
    ordenadas = sorted(cuenta, key=lambda r: (-cuenta[r], -max(len(f) for f in forma[r]), r))
    return [max(forma[r], key=forma[r].get) for r in ordenadas[:n]]


def cobertura(referencia: str, respuesta: str, n: int = 12) -> dict:
    """Qué palabras clave de la referencia aparecen en tu respuesta: {clave, cubiertos, faltan, porcentaje}."""
    clave = terminos_clave(referencia, n)
    mias = set(tokenizar(respuesta))
    cubiertos = [w for w in clave if set(tokenizar(w)) & mias]
    faltan = [w for w in clave if w not in cubiertos]
    return {"clave": clave, "cubiertos": cubiertos, "faltan": faltan,
            "porcentaje": round(100 * len(cubiertos) / len(clave)) if clave else 0}


def revisar_explicacion_local(texto: str, referencia: str = "") -> dict:
    """Revisión sin IA de una explicación «para un niño de 12 años»: longitud, frases largas y palabras técnicas."""
    frases = [f.strip() for f in _FRASE.split(texto.strip()) if f.strip()]
    palabras = re.findall(r"[^\W\d_]+", texto, re.UNICODE)
    largas = [f for f in frases if len(f.split()) > 28]
    tecnicas = sorted({w.lower() for w in palabras if len(w) >= 12})
    r = {"palabras": len(palabras), "frases": len(frases), "largas": largas, "tecnicas": tecnicas,
         "muy_corta": len(palabras) < 25, "cobertura": cobertura(referencia, texto) if referencia.strip() else None}
    return r


# ---------- evaluación con IA (solo con la referencia) ----------
_SIS_EVAL = ("Eres un tutor exigente pero amable. Comparas la respuesta del estudiante con el TEXTO DE REFERENCIA y usas "
             "SOLO ese texto como verdad. No añades datos que no estén en la referencia. Responde en el idioma del estudiante.")


def prompt_recuperacion(referencia: str, respuesta: str) -> str:
    return (f"TEXTO DE REFERENCIA:\n{referencia[:2500]}\n\nRESPUESTA DEL ESTUDIANTE (de memoria):\n{respuesta[:1500]}\n\n"
            "Responde exactamente con tres secciones, cada una con viñetas cortas que empiezan por «- »:\n"
            "CORRECTO:\nFALTA:\nERRORES:\n"
            "En FALTA pon las ideas importantes de la referencia que el estudiante no mencionó. "
            "En ERRORES pon lo que dijo y contradice la referencia. Si no hay nada, escribe «- ninguno».")


def _secciones(texto: str, nombres: tuple[str, ...]) -> dict[str, list[str]]:
    out = {n.lower(): [] for n in nombres}
    actual = None
    for linea in texto.splitlines():
        s = linea.strip()
        cab = re.match(r"^\W*(" + "|".join(nombres) + r")\s*:?\W*(.*)$", s, re.I)
        if cab and (cab.group(2) == "" or s.upper().startswith(cab.group(1).upper() + ":")):
            actual = cab.group(1).lower()
            resto = cab.group(2).strip(" -•*")
            if resto:
                out[actual].append(resto)
            continue
        if actual and s:
            item = s.lstrip("-•*0123456789.) ").strip()
            if item and item.lower() not in ("ninguno", "ninguna", "none", "nada"):
                out[actual].append(item)
    return {k: [x for x in v if x.lower() not in ("ninguno", "ninguna", "none", "nada")] for k, v in out.items()}


def parse_evaluacion(texto: str) -> dict:
    s = _secciones(texto, ("CORRECTO", "FALTA", "ERRORES"))
    return {"correcto": s["correcto"], "falta": s["falta"], "errores": s["errores"]}


def evaluar_recuperacion_ia(referencia: str, respuesta: str, llm=None) -> dict:
    if llm is None:
        from engine import ai
        llm = ai._llm
    return parse_evaluacion(llm(prompt_recuperacion(referencia, respuesta), _SIS_EVAL, 400))


def prompt_feynman(explicacion: str, referencia: str = "", edad: int = 12) -> str:
    ref = (f"TEXTO DE REFERENCIA (la verdad):\n{referencia[:2000]}\n\n" if referencia.strip() else
           "No hay texto de referencia: NO verifiques datos, solo la claridad.\n\n")
    return (f"{ref}EXPLICACIÓN DEL ESTUDIANTE (para alguien de {edad} años):\n{explicacion[:1500]}\n\n"
            f"Actúa como un estudiante curioso de {edad} años que acaba de oír esa explicación. Responde con tres secciones, "
            "cada una con viñetas cortas que empiezan por «- »:\nCLARO:\nHUECOS:\nPREGUNTAS:\n"
            "En HUECOS pon las palabras técnicas sin explicar y los saltos de lógica. En PREGUNTAS pon tres preguntas "
            "ingenuas que un niño haría y que el estudiante debería poder contestar.")


def parse_feynman(texto: str) -> dict:
    s = _secciones(texto, ("CLARO", "HUECOS", "PREGUNTAS"))
    return {"claro": s["claro"], "huecos": s["huecos"], "preguntas": s["preguntas"]}


def revisar_explicacion_ia(explicacion: str, referencia: str = "", llm=None, edad: int = 12) -> dict:
    if llm is None:
        from engine import ai
        llm = ai._llm
    return parse_feynman(llm(prompt_feynman(explicacion, referencia, edad), _SIS_EVAL, 400))


# ---------- simulacros ----------
@dataclass
class Pregunta:
    tarjeta_id: int
    enunciado: str
    correcta: str
    opciones: list[str] | None = None        # None = respuesta abierta (te corriges tú)
    tema: str = ""


def plano(texto: str) -> str:
    """Texto sin las marcas de glifo de las tarjetas de Owee (`[glifo]ka` → `ka`), para usarlo en una lista de opciones."""
    return re.sub(r"^\[(glifo|owee)\]", "", texto)


def _parecidas(correcta: str, candidatas: list[str], k: int, rng: random.Random) -> list[str]:
    """k respuestas incorrectas verosímiles: distintas entre sí y de largo parecido a la correcta."""
    vistas, pool = {plano(correcta).strip().lower()}, []
    for c in candidatas:
        clave = plano(c).strip().lower()
        if clave and clave not in vistas:
            vistas.add(clave)
            pool.append(c)
    largo = max(1, len(plano(correcta)))
    pool.sort(key=lambda c: (abs(len(plano(c)) - largo) / largo, rng.random()))
    cercanas = pool[:max(k * 3, k)]
    rng.shuffle(cercanas)
    return cercanas[:k]


def tarjetas_del_alcance(conn, perfil_id: int, plan_id: int | None = None, tema_id: int | None = None):
    sql = """SELECT k.*, t.titulo tema, u.plan_id FROM tarjetas k JOIN temas t ON t.id=k.tema_id
             JOIN unidades u ON u.id=t.unidad_id JOIN planes p ON p.id=u.plan_id WHERE p.perfil_id=?"""
    args: list = [perfil_id]
    if tema_id:
        sql, args = sql + " AND k.tema_id=?", args + [tema_id]
    elif plan_id:
        sql, args = sql + " AND p.id=?", args + [plan_id]
    return conn.execute(sql + " ORDER BY k.id", args).fetchall()


def preparar_simulacro(conn, perfil_id: int, plan_id: int | None = None, tema_id: int | None = None, n: int = 10,
                       tipo: str = "mixto", semilla: int | None = None) -> list[Pregunta]:
    """Examen con tus propias tarjetas. `tipo`: «opciones» (opción múltiple), «abierta» (te corriges tú) o «mixto».
    Las de opción múltiple usan como distractores las respuestas de otras tarjetas; si no hay suficientes, la
    pregunta queda abierta."""
    rng = random.Random(semilla)
    tarjetas = list(tarjetas_del_alcance(conn, perfil_id, plan_id, tema_id))
    rng.shuffle(tarjetas)
    todas = [k["respuesta"] for k in tarjetas]
    out = []
    for i, k in enumerate(tarjetas[:max(1, n)]):
        multiple = tipo == "opciones" or (tipo == "mixto" and i % 2 == 0)
        opciones = None
        if multiple:
            malas = _parecidas(k["respuesta"], todas, 3, rng)
            if len(malas) == 3:
                opciones = malas + [k["respuesta"]]
                rng.shuffle(opciones)
        out.append(Pregunta(k["id"], k["pregunta"], k["respuesta"], opciones, k["tema"]))
    return out


def corregir(preguntas: list[Pregunta], respuestas: dict[int, str | bool]) -> dict:
    """`respuestas`: tarjeta_id → opción elegida (múltiple) o True/False si te corregiste (abierta).
    Sin responder = incorrecta. Devuelve {total, correctas, porcentaje, errores:[Pregunta]}."""
    errores, bien = [], 0
    for p in preguntas:
        r = respuestas.get(p.tarjeta_id)
        ok = (r == p.correcta) if p.opciones else (r is True)
        if ok:
            bien += 1
        else:
            errores.append(p)
    total = len(preguntas)
    return {"total": total, "correctas": bien, "porcentaje": round(100 * bien / total) if total else 0, "errores": errores}


def reprogramar_errores(conn, errores: list[Pregunta]) -> int:
    """Cada tarjeta fallada cuenta como «otra vez» en tu calendario de repaso: vuelve a salir pronto."""
    from database import repo
    for p in errores:
        repo.repasar_tarjeta(conn, p.tarjeta_id, 1)
    return len(errores)


# ---------- historial ----------
def registrar(conn, plan_id: int, tipo: str, puntaje: float | None, detalle: dict | None = None, tema_id: int | None = None) -> int:
    if tipo not in TIPOS:
        raise ValueError("tipo de práctica desconocido")
    cur = conn.execute("INSERT INTO practicas(plan_id,tema_id,tipo,puntaje,detalle) VALUES (?,?,?,?,?)",
                       (plan_id, tema_id, tipo, puntaje, json.dumps(detalle or {}, ensure_ascii=False)))
    conn.commit()
    return cur.lastrowid


def historial(conn, plan_id: int, tipo: str | None = None, limite: int = 8):
    sql, args = "SELECT * FROM practicas WHERE plan_id=?", [plan_id]
    if tipo:
        sql, args = sql + " AND tipo=?", args + [tipo]
    return conn.execute(sql + " ORDER BY id DESC LIMIT ?", args + [limite]).fetchall()


def resumen(conn, plan_id: int) -> dict:
    """Por tipo: cuántas prácticas y el puntaje medio."""
    out = {x: {"n": 0, "media": None} for x in TIPOS}
    for r in conn.execute("SELECT tipo, COUNT(*) n, AVG(puntaje) m FROM practicas WHERE plan_id=? GROUP BY tipo", (plan_id,)):
        out[r["tipo"]] = {"n": r["n"], "media": None if r["m"] is None else round(r["m"])}
    return out


# ---------- referencias para comparar ----------
def referencia_de_tema(conn, tema_id: int, limite: int = 3000) -> str:
    """Lo que ya sabes del tema: tus tarjetas (pregunta y respuesta) y tus resúmenes anteriores."""
    partes = [f"{k['pregunta']} {k['respuesta']}" for k in conn.execute("SELECT * FROM tarjetas WHERE tema_id=? ORDER BY id", (tema_id,))]
    return "\n".join(partes)[:limite]


def referencia_de_lectura(conn, lectura_id: int, limite: int = 3000) -> str:
    l = conn.execute("SELECT * FROM lecturas WHERE id=?", (lectura_id,)).fetchone()
    campos = ("pregunta", "metodo", "hallazgos", "limitaciones", "utilidad", "cita_clave", "notas")
    return "\n".join((l[k] or "").strip() for k in campos if (l[k] or "").strip())[:limite]
