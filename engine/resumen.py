"""Resumen de la semana para compartir con la familia o con un docente.

Solo números y títulos: racha, horas, repasos, prácticas, retos y entregas próximas. Nunca el contenido de tus notas, tarjetas,
lecturas ni escritos. Lo compartes tú, copiando el texto o guardándolo en un archivo: la app no envía nada a nadie.
"""
import html as _html
from datetime import date, timedelta

from database import repo
from engine import retos as rt
from engine import sprints as sp
from i18n import t, tn


def resumen(conn, perfil_id: int, plan_id: int | None = None, hoy: date | None = None, dias: int = 7) -> dict:
    hoy = hoy or date.today()
    desde = (hoy - timedelta(days=dias - 1)).isoformat()
    perfil = next((p for p in repo.perfiles(conn) if p["id"] == perfil_id), None)
    filtro = " AND p.id=?" if plan_id else ""
    args = [perfil_id] + ([plan_id] if plan_id else [])
    repasos = conn.execute(f"""SELECT COUNT(*) n, SUM(r.calidad>=3) bien FROM repasos_log r JOIN temas t ON t.id=r.tema_id JOIN unidades u ON u.id=t.unidad_id
                               JOIN planes p ON p.id=u.plan_id WHERE p.perfil_id=? {filtro} AND r.fecha>=?""", args + [desde]).fetchone()
    practicas = conn.execute(f"""SELECT x.tipo, COUNT(*) n, AVG(x.puntaje) media FROM practicas x JOIN planes p ON p.id=x.plan_id
                                 WHERE p.perfil_id=? {filtro} AND x.fecha>=? GROUP BY x.tipo""", args + [desde]).fetchall()
    planes = [p for p in repo.planes(conn, perfil_id) if not plan_id or p["id"] == plan_id]
    retos_hechos = conn.execute(f"""SELECT COUNT(*) FROM retos r JOIN planes p ON p.id=r.plan_id WHERE p.perfil_id=? {filtro}
                                    AND r.estado='hecho' AND r.hecho_en>=?""", args + [desde]).fetchone()[0]
    entregas = [e for e in repo.entregas(conn, perfil_id, plan_id, "pendiente") if e["dias"] <= 14]
    s = sp.sprint_activo(conn, perfil_id, plan_id)
    return {
        "nombre": perfil["nombre"] if perfil else "", "nivel": perfil["nivel"] if perfil else "", "dias": dias, "hasta": hoy.isoformat(),
        "racha": repo.racha(conn, perfil_id), "horas": round(repo.horas_semana(conn, perfil_id), 1),
        "repasos": repasos["n"] or 0, "repasos_bien": repasos["bien"] or 0,
        "pendientes": len(repo.tarjetas_pendientes(conn, perfil_id)) + len(repo.repasos_pendientes(conn, perfil_id)),
        "practicas": {p["tipo"]: {"n": p["n"], "media": None if p["media"] is None else round(p["media"])} for p in practicas},
        "retos_hechos": retos_hechos, "retos_abiertos": len([r for r in rt.retos(conn, perfil_id, plan_id, "pendiente")]),
        "asignaturas": [{"titulo": p["titulo"], "progreso": round(100 * repo.progreso(conn, p["id"]))} for p in planes],
        "entregas": [{"titulo": e["titulo"], "plan": e["plan"], "fecha": e["fecha"], "dias": e["dias"], "tipo": e["tipo"]} for e in entregas],
        "sprint": None if s is None else {"titulo": s["titulo"], **sp.progreso(conn, s["id"])},
    }


def _nombre_practica(tipo: str) -> str:
    return {"recuperacion": t("recuperación libre"), "feynman": t("explicaciones (Feynman)"), "simulacro": t("simulacros")}[tipo]


def lineas(r: dict) -> list[tuple[str, list[str]]]:
    """El resumen como [(título de sección, [líneas])]: sirve para texto, Markdown y HTML."""
    sec = [(t("Esta semana"), [
        tn(r["racha"], "Racha: {n} día seguido", "Racha: {n} días seguidos"),
        t("Horas de estudio (últimos 7 días): {h:.1f}", h=r["horas"]),
        t("Repasos hechos: {n} ({b} bien recordados)", n=r["repasos"], b=r["repasos_bien"]),
        t("Repasos pendientes hoy: {n}", n=r["pendientes"])])]
    if r["practicas"]:
        sec.append((t("Práctica activa"), [t("{tipo}: {n} (media {m}%)", tipo=_nombre_practica(k), n=v["n"], m=v["media"] if v["media"] is not None else 0)
                                           for k, v in r["practicas"].items()]))
    extra = []
    if r["retos_hechos"] or r["retos_abiertos"]:
        extra.append(t("Retos cumplidos esta semana: {a} · abiertos: {b}", a=r["retos_hechos"], b=r["retos_abiertos"]))
    if r["sprint"]:
        extra.append(t("Sprint de 7 días: {a} de {b} pasos hechos", a=r["sprint"]["hechas"], b=r["sprint"]["total"]))
    if extra:
        sec.append((t("Aplicación"), extra))
    if r["asignaturas"]:
        sec.append((t("Avance por asignatura"), [f"{a['titulo']}: {a['progreso']}%" for a in r["asignaturas"]]))
    if r["entregas"]:
        from ui.views.entregas import cuando
        sec.append((t("Próximas entregas y exámenes"), [f"{e['titulo']} ({e['plan']}) · {e['fecha']} · {cuando(e['dias'])}" for e in r["entregas"]]))
    return sec


def a_texto(r: dict) -> str:
    cab = t("Resumen de estudio de {nombre} (hasta el {fecha})", nombre=r["nombre"], fecha=r["hasta"])
    partes = [cab]
    for titulo, ls in lineas(r):
        partes += ["", titulo.upper()] + [f"• {x}" for x in ls]
    partes += ["", t("Solo incluye cifras y títulos; no el contenido de las notas.")]
    return "\n".join(partes) + "\n"


def a_html(r: dict) -> str:
    cab = t("Resumen de estudio de {nombre} (hasta el {fecha})", nombre=r["nombre"], fecha=r["hasta"])
    cuerpo = [f"<h1>{_html.escape(cab)}</h1>"]
    for titulo, ls in lineas(r):
        cuerpo.append(f"<h2>{_html.escape(titulo)}</h2><ul>" + "".join(f"<li>{_html.escape(x)}</li>" for x in ls) + "</ul>")
    cuerpo.append(f"<p><small>{_html.escape(t('Solo incluye cifras y títulos; no el contenido de las notas.'))}</small></p>")
    return ('<!doctype html>\n<html><head><meta charset="utf-8"><title>OweeStudent</title><style>body{font-family:system-ui,sans-serif;max-width:40em;'
            'margin:2em auto;padding:0 1em;line-height:1.5}h2{border-bottom:1px solid #ccc;padding-bottom:.2em}</style></head><body>\n'
            + "\n".join(cuerpo) + "\n</body></html>\n")


