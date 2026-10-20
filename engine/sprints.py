"""Sprints de 7 días: una semana intensiva sobre UN tema, con un paso por día que combina lo que ya hace la app.

Ciclo: explorar → entender → practicar → fijar → recordar → probarte → corregir. Lo que dice la investigación sobre aprendizaje:
primero comprender, después aplicar y, sobre todo, intentar recordar y examinarse, y dedicar el último día a lo que fallaste.
"""
from datetime import date

from i18n import marcar, t

DIAS = 7
# (clave de acción, texto del paso): la clave dice a qué pantalla lleva el botón «Ir»
PASOS = (("material", marcar("Explorar: lee o mira el material y anota las ideas clave")),
         ("feynman", marcar("Entender: explícalo con tus palabras, como a alguien de otra edad")),
         ("retos", marcar("Practicar: haz un reto de aplicación o varios ejercicios")),
         ("estudiar", marcar("Fijar: crea tarjetas del tema y repásalas")),
         ("recuperacion", marcar("Recordar: escribe de memoria todo lo que sabes del tema")),
         ("simulacro", marcar("Probarte: haz un simulacro del tema")),
         ("debiles", marcar("Cerrar: corrige tus errores y repasa tus puntos débiles")))


def crear_sprint(conn, plan_id: int, tema_id: int | None, inicio=None, titulo: str | None = None) -> int:
    inicio = inicio or date.today()
    inicio = inicio.isoformat() if hasattr(inicio, "isoformat") else date.fromisoformat(inicio).isoformat()
    tema = ""
    if tema_id:
        r = conn.execute("SELECT titulo FROM temas WHERE id=?", (tema_id,)).fetchone()
        tema = r["titulo"] if r else ""
    cur = conn.execute("INSERT INTO sprints(plan_id,tema_id,titulo,inicio) VALUES (?,?,?,?)",
                       (plan_id, tema_id, (titulo or t("Sprint de 7 días: {tema}", tema=tema or t("tu tema"))).strip(), inicio))
    sid = cur.lastrowid
    for dia, (accion, texto) in enumerate(PASOS, start=1):
        conn.execute("INSERT INTO sprint_tareas(sprint_id,dia,titulo,accion) VALUES (?,?,?,?)", (sid, dia, t(texto), accion))
    conn.commit()
    return sid


def sprint(conn, sprint_id):
    return conn.execute("""SELECT s.*, t.titulo tema, p.titulo plan FROM sprints s LEFT JOIN temas t ON t.id=s.tema_id
                           JOIN planes p ON p.id=s.plan_id WHERE s.id=?""", (sprint_id,)).fetchone()


def sprint_activo(conn, perfil_id: int, plan_id: int | None = None):
    """El sprint en marcha más reciente (o None)."""
    sql = """SELECT s.id FROM sprints s JOIN planes p ON p.id=s.plan_id WHERE p.perfil_id=? AND s.estado='activo'"""
    args: list = [perfil_id]
    if plan_id:
        sql, args = sql + " AND s.plan_id=?", args + [plan_id]
    r = conn.execute(sql + " ORDER BY s.id DESC LIMIT 1", args).fetchone()
    return sprint(conn, r["id"]) if r else None


def tareas(conn, sprint_id: int):
    return conn.execute("SELECT * FROM sprint_tareas WHERE sprint_id=? ORDER BY dia", (sprint_id,)).fetchall()


def dia_actual(s, hoy: date | None = None) -> int:
    """Qué día del sprint es hoy: 1 a 7; 0 si todavía no empieza y 8 si ya pasó la semana."""
    d = ((hoy or date.today()) - date.fromisoformat(s["inicio"])).days + 1
    return 0 if d < 1 else min(d, DIAS + 1)


def marcar_tarea(conn, tarea_id: int, hecha: bool):
    conn.execute("UPDATE sprint_tareas SET hecha=? WHERE id=?", (1 if hecha else 0, tarea_id))
    conn.commit()
    s = conn.execute("SELECT sprint_id FROM sprint_tareas WHERE id=?", (tarea_id,)).fetchone()
    if s and progreso(conn, s["sprint_id"])["hechas"] == DIAS:
        conn.execute("UPDATE sprints SET estado='terminado' WHERE id=?", (s["sprint_id"],))
        conn.commit()
    elif s:
        conn.execute("UPDATE sprints SET estado='activo' WHERE id=?", (s["sprint_id"],))
        conn.commit()


def progreso(conn, sprint_id: int) -> dict:
    ts = tareas(conn, sprint_id)
    hechas = sum(1 for x in ts if x["hecha"])
    return {"hechas": hechas, "total": len(ts), "porcentaje": round(100 * hechas / len(ts)) if ts else 0}


def tarea_de_hoy(conn, s, hoy: date | None = None):
    """El paso que toca: el primero que falta (los pasos van en orden: no tiene sentido practicar antes de entender).
    None si el sprint aún no empieza o ya está completo."""
    if dia_actual(s, hoy) == 0:
        return None
    return next((x for x in tareas(conn, s["id"]) if not x["hecha"]), None)


def va_atrasado(conn, s, hoy: date | None = None) -> bool:
    """¿Hay pasos de días anteriores a hoy sin hacer?"""
    d = min(dia_actual(s, hoy), DIAS)
    return any(not x["hecha"] and x["dia"] < d for x in tareas(conn, s["id"]))


def terminar(conn, sprint_id: int):
    conn.execute("UPDATE sprints SET estado='terminado' WHERE id=?", (sprint_id,))
    conn.commit()


def borrar(conn, sprint_id: int):
    conn.execute("DELETE FROM sprints WHERE id=?", (sprint_id,))
    conn.commit()


