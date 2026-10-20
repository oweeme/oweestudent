"""El curso de Owee dentro de la app: plan de estudio (niveles → lecciones) y tarjetas de glifos y vocabulario.

Las tarjetas guardan SOLO texto latino con una marca: `[glifo]ka` (se dibuja el glifo solo) o `[owee]suna` (glifo con
la romanización debajo). Los glifos (área privada de Unicode) nunca se guardan; se dibujan al mostrar la tarjeta.
"""
from database import repo
from i18n import owee
from owee_curso.bloques import palabras_de
from owee_curso.datos import LEXICO, NIVELES

TITULO_PLAN = "Aprende Owee"
CARPETA = "Owee"
MARCA_GLIFO, MARCA_OWEE = "[glifo]", "[owee]"
VOCALES_ID, SILABAS_ID, NUMEROS_ID = "0.1", "0.2", "0.4"     # lecciones donde se aprenden los glifos


def lecciones() -> list[dict]:
    """Todas las lecciones en orden, con su nivel."""
    return [{**l, "nivel": n["n"], "nivel_titulo": n["titulo"]} for n in NIVELES for l in n["lecciones"]]


def leccion(id_: str) -> dict | None:
    return next((l for l in lecciones() if l["id"] == id_), None)


def titulo_tema(l: dict) -> str:
    return f"{l['id']} {l['titulo']}"


def significado(palabra: str) -> str | None:
    r = LEXICO.get(palabra.lower())
    return r[0] if r else None


def _silabas() -> tuple[list[str], list[str]]:
    vocales = list(owee.VOCALES)
    cv = [c + v for c in owee.CONSONANTES for v in owee.VOCALES]
    return vocales, cv


def tarjetas_de_leccion(id_: str) -> list[tuple[str, str]]:
    """Pares (pregunta, respuesta) que se aprenden en una lección. Lo que no tiene significado en el léxico se omite:
    la app no inventa significados."""
    pares: list[tuple[str, str]] = []
    vocales, cv = _silabas()
    if id_ == VOCALES_ID:
        pares += [(MARCA_GLIFO + v, v) for v in vocales]
    elif id_ == SILABAS_ID:
        pares += [(MARCA_GLIFO + s, s) for s in cv]
    elif id_ == NUMEROS_ID:
        pares += [(f"{MARCA_GLIFO}{d}", str(d)) for d in range(10)]
    l = leccion(id_)
    for w in palabras_de(l["md"]) if l else []:
        s = significado(w)
        if s:
            pares += [(MARCA_OWEE + w, s), (s, MARCA_OWEE + w)]
    return pares


def crear_tarjetas_leccion(conn, plan_id: int, id_: str) -> int:
    """Crea (sin duplicar) las tarjetas de una lección en su tema del plan del curso. Devuelve cuántas nuevas."""
    l = leccion(id_)
    tema = _tema_de(conn, plan_id, l)
    if tema is None:
        return 0
    pares = tarjetas_de_leccion(id_)
    directas = [x for x in pares if not x[1].startswith(MARCA_OWEE)]
    inversas = [x for x in pares if x[1].startswith(MARCA_OWEE)]       # significado → palabra: se repasa escribiendo
    return repo.crear_tarjetas(conn, tema, directas, "owee") + repo.crear_tarjetas(conn, tema, inversas, "produccion")


def _tema_de(conn, plan_id: int, l: dict | None):
    if l is None:
        return None
    r = conn.execute("""SELECT t.id FROM temas t JOIN unidades u ON u.id=t.unidad_id
                        WHERE u.plan_id=? AND t.titulo=?""", (plan_id, titulo_tema(l))).fetchone()
    return r["id"] if r else None


def plan_del_curso(conn, perfil_id: int) -> int | None:
    r = conn.execute("SELECT id FROM planes WHERE perfil_id=? AND titulo=? ORDER BY id LIMIT 1",
                     (perfil_id, TITULO_PLAN)).fetchone()
    return r["id"] if r else None


def crear_plan_del_curso(conn, perfil_id: int, inicio=None) -> int:
    """Crea el plan «Aprende Owee» (una unidad por nivel, un tema por lección) en la carpeta «Owee».
    Es seguro repetirlo: si ya existe devuelve el mismo plan."""
    existente = plan_del_curso(conn, perfil_id)
    if existente:
        return existente
    carpeta = next((c["id"] for c in repo.carpetas(conn, perfil_id) if c["nombre"] == CARPETA), None) \
        or repo.crear_carpeta(conn, CARPETA, perfil_id)
    plan = repo.crear_plan(conn, TITULO_PLAN, perfil_id, inicio, carpeta_id=carpeta)
    for n in NIVELES:
        unidad = repo.agregar_unidad(conn, plan, f"Nivel {n['n']} — {n['titulo']}", tipo="idioma")
        for l in n["lecciones"]:
            repo.agregar_tema(conn, unidad, titulo_tema(l), horas=0.5 if n["n"] == 0 else 1.0)
    return plan


def siguiente_leccion(conn, plan_id: int) -> dict | None:
    """La primera lección que todavía no marcaste como hecha (None si terminaste el curso)."""
    return next((l for l in lecciones() if estado_leccion(conn, plan_id, l["id"]) != "completado"), None)


def estado_leccion(conn, plan_id: int, id_: str) -> str | None:
    t = _tema_de(conn, plan_id, leccion(id_))
    if t is None:
        return None
    return conn.execute("SELECT estado FROM temas WHERE id=?", (t,)).fetchone()["estado"]


def marcar_leccion(conn, plan_id: int, id_: str, hecha: bool):
    t = _tema_de(conn, plan_id, leccion(id_))
    if t is not None:
        repo.marcar_tema(conn, t, "completado" if hecha else "pendiente")
