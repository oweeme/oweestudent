"""Operaciones de alto nivel sobre la base de datos."""
import hashlib
import hmac
import json
import os
from datetime import date

from engine import fsrs
from engine.scheduler import programar_temas
from parsers.file_parser import extract_text
from parsers.plan_parser import parse_plan
from parsers.regex_extractor import extraer_urls


def importar_archivo(conn, ruta: str, inicio: date | None = None, perfil_id: int = 1,
                     plan_id: int | None = None) -> int:
    """Lee un archivo (txt/md/pdf/docx/xlsx) y lo guarda. Con plan_id lo AGREGA a ese plan."""
    return importar_texto(conn, extract_text(ruta), ruta.rsplit("/", 1)[-1], inicio, perfil_id, plan_id)


def importar_texto(conn, texto: str, nombre: str = "Plan pegado", inicio: date | None = None,
                   perfil_id: int = 1, plan_id: int | None = None) -> int:
    """Estructura `texto` y lo guarda como plan nuevo, o lo suma a `plan_id` existente."""
    plan = parse_plan(texto)
    if plan_id is None:
        inicio = inicio or date.today()
        plan_id = conn.execute(
            "INSERT INTO planes(titulo, archivo, meta, fecha_inicio, perfil_id) VALUES (?,?,?,?,?)",
            (plan["titulo"] or nombre, nombre, json.dumps(plan["meta"], ensure_ascii=False),
             inicio.isoformat(), perfil_id)).lastrowid
    else:
        row = conn.execute("SELECT fecha_inicio FROM planes WHERE id=?", (plan_id,)).fetchone()
        inicio = inicio or date.fromisoformat(row["fecha_inicio"])
    base = conn.execute("SELECT COALESCE(MAX(orden)+1,0) FROM unidades WHERE plan_id=?", (plan_id,)).fetchone()[0]

    for orden, u in enumerate(plan["unidades"], start=base):
        uid = conn.execute(
            "INSERT INTO unidades(plan_id,titulo,semestre,tipo,mes_ini,mes_fin,orden) VALUES (?,?,?,?,?,?,?)",
            (plan_id, u["titulo"], u["semestre"], u["tipo"], u["mes_ini"], u["mes_fin"], orden)).lastrowid
        tids = [conn.execute("INSERT INTO temas(unidad_id,titulo,orden) VALUES (?,?,?)",
                             (uid, t, i)).lastrowid for i, t in enumerate(u["temas"])]
        for tid, f in programar_temas(u, tids, inicio):
            conn.execute("UPDATE temas SET fecha_programada=? WHERE id=?", (f, tid))
        for b in u["libros"]:
            conn.execute("INSERT INTO recursos(unidad_id,tipo,contenido,descripcion) VALUES (?,?,?,?)",
                         (uid, "libro", b["titulo"], b["autor"]))
        for tipo, items in (("busqueda", u["busqueda"]), ("alternativa", u["alternativas"])):
            for it in items:
                conn.execute("INSERT INTO recursos(unidad_id,tipo,contenido) VALUES (?,?,?)", (uid, tipo, it))
                for url in extraer_urls(it):
                    conn.execute("INSERT INTO recursos(unidad_id,tipo,contenido) VALUES (?,?,?)", (uid, "url", url))
        if u["entregable"]:
            e = u["entregable"]
            conn.execute("INSERT INTO entregables(unidad_id,titulo,descripcion) VALUES (?,?,?)",
                         (uid, e["titulo"], e["descripcion"]))
        for idm in u["idiomas"]:
            conn.execute("INSERT INTO metas_idioma(unidad_id,idioma,objetivo,detalle) VALUES (?,?,?,?)",
                         (uid, idm["nombre"].split("(")[0].strip(), idm["nombre"], "\n".join(idm["detalles"])))
    for fila in plan["cronograma"]:
        for bloque, act in fila["bloques"].items():
            conn.execute("INSERT INTO cronograma(plan_id,dia,bloque,actividad) VALUES (?,?,?,?)",
                         (plan_id, fila["dia"], bloque, act))
    conn.commit()
    return plan_id


def planes(conn, perfil_id=None):
    if perfil_id is None:
        return conn.execute("SELECT * FROM planes ORDER BY id DESC").fetchall()
    return conn.execute("SELECT * FROM planes WHERE perfil_id=? ORDER BY id DESC", (perfil_id,)).fetchall()


def perfiles(conn):
    return conn.execute("SELECT * FROM perfiles ORDER BY id").fetchall()


def crear_perfil(conn, nombre, nivel="universitario", clave: str | None = None) -> int:
    cur = conn.execute("INSERT INTO perfiles(nombre, nivel) VALUES (?,?)", (nombre, nivel))
    conn.commit()
    if clave:
        fijar_clave(conn, cur.lastrowid, clave)
    return cur.lastrowid


def crear_plan(conn, titulo, perfil_id=1, inicio=None) -> int:
    cur = conn.execute("INSERT INTO planes(titulo, fecha_inicio, perfil_id) VALUES (?,?,?)",
                       (titulo, (inicio or date.today()).isoformat(), perfil_id))
    conn.commit()
    return cur.lastrowid


def borrar_plan(conn, plan_id):
    conn.execute("DELETE FROM planes WHERE id=?", (plan_id,))
    conn.commit()


def agregar_unidad(conn, plan_id, titulo, tipo="modulo", mes_ini=None, mes_fin=None) -> int:
    orden = conn.execute("SELECT COALESCE(MAX(orden)+1,0) FROM unidades WHERE plan_id=?", (plan_id,)).fetchone()[0]
    cur = conn.execute("INSERT INTO unidades(plan_id,titulo,tipo,mes_ini,mes_fin,orden) VALUES (?,?,?,?,?,?)",
                       (plan_id, titulo, tipo, mes_ini, mes_fin, orden))
    conn.commit()
    return cur.lastrowid


def agregar_tema(conn, unidad_id, titulo, fecha=None, horas=1.5) -> int:
    orden = conn.execute("SELECT COALESCE(MAX(orden)+1,0) FROM temas WHERE unidad_id=?", (unidad_id,)).fetchone()[0]
    cur = conn.execute("INSERT INTO temas(unidad_id,titulo,fecha_programada,horas_estimadas,orden) VALUES (?,?,?,?,?)",
                       (unidad_id, titulo, fecha, horas, orden))
    conn.commit()
    return cur.lastrowid


def agregar_recurso(conn, unidad_id, contenido, tipo="url", descripcion=None):
    conn.execute("INSERT INTO recursos(unidad_id,tipo,contenido,descripcion) VALUES (?,?,?,?)",
                 (unidad_id, tipo, contenido, descripcion))
    conn.commit()


def agregar_cronograma(conn, plan_id, dia, bloque, actividad):
    conn.execute("INSERT INTO cronograma(plan_id,dia,bloque,actividad) VALUES (?,?,?,?)",
                 (plan_id, dia, bloque, actividad))
    conn.commit()


def unidades(conn, plan_id):
    return conn.execute("SELECT * FROM unidades WHERE plan_id=? ORDER BY orden", (plan_id,)).fetchall()


def temas(conn, unidad_id):
    return conn.execute("SELECT * FROM temas WHERE unidad_id=? ORDER BY orden", (unidad_id,)).fetchall()


def recursos(conn, unidad_id):
    return conn.execute("SELECT * FROM recursos WHERE unidad_id=? ORDER BY tipo,id", (unidad_id,)).fetchall()


def progreso(conn, plan_id) -> float:
    r = conn.execute("""SELECT COUNT(*) n, SUM(t.estado='completado') c FROM temas t
        JOIN unidades u ON u.id=t.unidad_id WHERE u.plan_id=?""", (plan_id,)).fetchone()
    return (r["c"] or 0) / r["n"] if r["n"] else 0.0


def marcar_tema(conn, tema_id, estado):
    conn.execute("UPDATE temas SET estado=? WHERE id=?", (estado, tema_id))
    conn.commit()


def registrar_sesion(conn, tema_id, minutos):
    conn.execute("INSERT INTO sesiones(tema_id,minutos) VALUES (?,?)", (tema_id, minutos))
    if tema_id:
        conn.execute("UPDATE temas SET horas_dedicadas=horas_dedicadas+?, estado=CASE WHEN estado='pendiente' THEN 'en_proceso' ELSE estado END WHERE id=?",
                     (minutos / 60, tema_id))
    conn.commit()


def guardar_nota(conn, tema_id, resumen, calidad):
    e = fsrs.revisar(None, None, None, calidad)
    conn.execute("""INSERT INTO notas(tema_id,resumen_propio,dificultad,proximo_repaso,intervalo_dias,repeticiones,
                    estabilidad,dificultad_fsrs,ultimo_repaso) VALUES (?,?,?,?,?,?,?,?,?)""",
                 (tema_id, resumen, calidad, e["proximo"], e["intervalo"], 1, e["estabilidad"], e["dificultad"], e["ultimo"]))
    conn.commit()
    return e["proximo"]


def repasos_pendientes(conn, perfil_id=1):
    return conn.execute("""SELECT n.*, t.titulo tema FROM notas n JOIN temas t ON t.id=n.tema_id
        JOIN unidades u ON u.id=t.unidad_id JOIN planes p ON p.id=u.plan_id
        WHERE p.perfil_id=? AND n.proximo_repaso<=date('now','localtime')
        ORDER BY n.proximo_repaso""", (perfil_id,)).fetchall()


def repasar(conn, nota_id, calidad):
    n = conn.execute("SELECT * FROM notas WHERE id=?", (nota_id,)).fetchone()
    e = fsrs.revisar(n["estabilidad"], n["dificultad_fsrs"], n["ultimo_repaso"], calidad)
    conn.execute("""UPDATE notas SET repeticiones=repeticiones+1,intervalo_dias=?,proximo_repaso=?,dificultad=?,
                    estabilidad=?,dificultad_fsrs=?,ultimo_repaso=? WHERE id=?""",
                 (e["intervalo"], e["proximo"], calidad, e["estabilidad"], e["dificultad"], e["ultimo"], nota_id))
    conn.execute("INSERT INTO repasos_log(tema_id,tipo,calidad) VALUES (?,?,?)", (n["tema_id"], "nota", calidad))
    conn.commit()


_SES = """FROM sesiones s JOIN temas t ON t.id=s.tema_id JOIN unidades u ON u.id=t.unidad_id
    JOIN planes p ON p.id=u.plan_id WHERE p.perfil_id=?"""


def racha(conn, perfil_id=1) -> int:
    from datetime import timedelta
    dias = {r[0] for r in conn.execute("SELECT DISTINCT s.fecha " + _SES, (perfil_id,))}
    d, n = date.today(), 0
    if d.isoformat() not in dias:
        d -= timedelta(days=1)
    while d.isoformat() in dias:
        n, d = n + 1, d - timedelta(days=1)
    return n


def horas_semana(conn, perfil_id=1) -> float:
    r = conn.execute("SELECT SUM(s.minutos) " + _SES + " AND s.fecha>=date('now','localtime','-6 day')",
                     (perfil_id,)).fetchone()
    return (r[0] or 0) / 60


def editar_tema(conn, tema_id, titulo, fecha=None, horas=None):
    conn.execute("UPDATE temas SET titulo=?, fecha_programada=?, horas_estimadas=COALESCE(?,horas_estimadas) WHERE id=?",
                 (titulo, fecha, horas, tema_id))
    conn.commit()


def borrar_tema(conn, tema_id):
    conn.execute("DELETE FROM temas WHERE id=?", (tema_id,))
    conn.commit()


def renombrar_unidad(conn, unidad_id, titulo):
    conn.execute("UPDATE unidades SET titulo=? WHERE id=?", (titulo, unidad_id))
    conn.commit()


def borrar_unidad(conn, unidad_id):
    conn.execute("DELETE FROM unidades WHERE id=?", (unidad_id,))
    conn.commit()


def borrar_recurso(conn, recurso_id):
    conn.execute("DELETE FROM recursos WHERE id=?", (recurso_id,))
    conn.commit()


def cronograma(conn, plan_id):
    return conn.execute("SELECT * FROM cronograma WHERE plan_id=? ORDER BY id", (plan_id,)).fetchall()


def borrar_cronograma(conn, fila_id):
    conn.execute("DELETE FROM cronograma WHERE id=?", (fila_id,))
    conn.commit()


def crear_tarjeta(conn, tema_id, pregunta, respuesta, origen="manual"):
    conn.execute("INSERT INTO tarjetas(tema_id,pregunta,respuesta,origen) VALUES (?,?,?,?)",
                 (tema_id, pregunta.strip(), respuesta.strip(), origen))
    conn.commit()


def crear_tarjetas(conn, tema_id, pares, origen) -> int:
    """Inserta varias evitando duplicados de pregunta en el mismo tema."""
    n = 0
    for p, r in pares:
        if not p.strip() or not r.strip():
            continue
        if conn.execute("SELECT 1 FROM tarjetas WHERE tema_id=? AND pregunta=?", (tema_id, p.strip())).fetchone():
            continue
        conn.execute("INSERT INTO tarjetas(tema_id,pregunta,respuesta,origen) VALUES (?,?,?,?)",
                     (tema_id, p.strip(), r.strip(), origen))
        n += 1
    conn.commit()
    return n


def tarjetas_pendientes(conn, perfil_id=1):
    return conn.execute("""SELECT k.*, t.titulo tema FROM tarjetas k JOIN temas t ON t.id=k.tema_id
        JOIN unidades u ON u.id=t.unidad_id JOIN planes p ON p.id=u.plan_id
        WHERE p.perfil_id=? AND k.proximo_repaso<=date('now','localtime')
        ORDER BY k.proximo_repaso, k.id""", (perfil_id,)).fetchall()


def tarjetas_tema(conn, tema_id):
    return conn.execute("SELECT * FROM tarjetas WHERE tema_id=? ORDER BY id", (tema_id,)).fetchall()


def borrar_tarjeta(conn, tarjeta_id):
    conn.execute("DELETE FROM tarjetas WHERE id=?", (tarjeta_id,))
    conn.commit()


def repasar_tarjeta(conn, tarjeta_id, calidad):
    k = conn.execute("SELECT * FROM tarjetas WHERE id=?", (tarjeta_id,)).fetchone()
    e = fsrs.revisar(k["estabilidad"], k["dificultad_fsrs"], k["ultimo_repaso"], calidad)
    conn.execute("""UPDATE tarjetas SET repeticiones=repeticiones+1,intervalo_dias=?,proximo_repaso=?,
                    estabilidad=?,dificultad_fsrs=?,ultimo_repaso=? WHERE id=?""",
                 (e["intervalo"], e["proximo"], e["estabilidad"], e["dificultad"], e["ultimo"], tarjeta_id))
    conn.execute("INSERT INTO repasos_log(tema_id,tipo,calidad) VALUES (?,?,?)", (k["tema_id"], "tarjeta", calidad))
    conn.commit()


def retencion(conn, perfil_id=1, dias=30):
    """(% de repasos con calidad >= 3, total de repasos) en los últimos `dias`."""
    r = conn.execute("""SELECT COUNT(*) n, SUM(l.calidad>=3) ok FROM repasos_log l JOIN temas t ON t.id=l.tema_id
        JOIN unidades u ON u.id=t.unidad_id JOIN planes p ON p.id=u.plan_id
        WHERE p.perfil_id=? AND l.fecha>=date('now','localtime',?)""", (perfil_id, f"-{dias} day")).fetchone()
    return ((r["ok"] or 0) / r["n"] if r["n"] else None), r["n"]


def meta_semanal(conn, plan_id) -> float:
    r = conn.execute("SELECT horas_semana FROM planes WHERE id=?", (plan_id,)).fetchone()
    return (r["horas_semana"] if r and r["horas_semana"] else 12.0)


# ---------- Claves de acceso (por perfil, opcionales) ----------
def _hash(clave: str, sal: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", clave.encode(), sal, 200_000).hex()


def tiene_clave(conn, perfil_id) -> bool:
    r = conn.execute("SELECT clave_hash FROM perfiles WHERE id=?", (perfil_id,)).fetchone()
    return bool(r and r["clave_hash"])


def fijar_clave(conn, perfil_id, clave: str | None):
    """Pone o cambia la clave del perfil; None o vacío la quita. Se guarda solo un hash con sal."""
    if clave:
        sal = os.urandom(16)
        conn.execute("UPDATE perfiles SET clave_hash=?, sal=? WHERE id=?", (_hash(clave, sal), sal.hex(), perfil_id))
    else:
        conn.execute("UPDATE perfiles SET clave_hash=NULL, sal=NULL WHERE id=?", (perfil_id,))
    conn.commit()


def verificar_clave(conn, perfil_id, clave: str) -> bool:
    r = conn.execute("SELECT clave_hash, sal FROM perfiles WHERE id=?", (perfil_id,)).fetchone()
    if not r or not r["clave_hash"]:
        return True
    return hmac.compare_digest(_hash(clave or "", bytes.fromhex(r["sal"])), r["clave_hash"])


def hay_claves(conn) -> bool:
    return conn.execute("SELECT 1 FROM perfiles WHERE clave_hash IS NOT NULL").fetchone() is not None
