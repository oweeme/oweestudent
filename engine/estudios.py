"""Vista de conjunto de «Mis estudios»: carpetas → planes con su avance y el siguiente tema."""
from database import repo
from i18n import t
from owee_curso.curso import TITULO_PLAN as TITULO_CURSO_OWEE


def resumen(conn, plan_id: int) -> dict:
    """Temas hechos/total, progreso, siguiente tema pendiente y cuántos materiales tiene el plan."""
    r = conn.execute("""SELECT COUNT(*) n, COALESCE(SUM(t.estado='completado'),0) ok FROM temas t
                        JOIN unidades u ON u.id=t.unidad_id WHERE u.plan_id=?""", (plan_id,)).fetchone()
    sig = conn.execute("""SELECT t.id, t.titulo, u.titulo AS unidad FROM temas t JOIN unidades u ON u.id=t.unidad_id
                          WHERE u.plan_id=? AND t.estado!='completado' ORDER BY u.orden, t.orden, t.id LIMIT 1""",
                       (plan_id,)).fetchone()
    mats = conn.execute("SELECT COUNT(*) FROM materiales WHERE plan_id=?", (plan_id,)).fetchone()[0]
    return {"temas": r["n"], "hechos": r["ok"], "progreso": (r["ok"] / r["n"]) if r["n"] else 0.0,
            "siguiente": dict(sig) if sig else None, "materiales": mats}


def arbol(conn, perfil_id: int) -> list[tuple[dict | None, list[dict]]]:
    """[(carpeta o None, [planes con su resumen])]. El curso opcional de Owee va siempre al final."""
    def con_resumen(ps):
        return [{**dict(p), **resumen(conn, p["id"]), "opcional": p["titulo"] == TITULO_CURSO_OWEE} for p in ps]
    grupos = [(dict(k), con_resumen(repo.planes_de_carpeta(conn, perfil_id, k["id"]))) for k in repo.carpetas(conn, perfil_id)]
    sueltas = con_resumen(repo.planes_de_carpeta(conn, perfil_id, None))
    propias = [p for p in sueltas if not p["opcional"]]
    opcionales = [p for p in sueltas if p["opcional"]]
    if propias or not grupos:
        grupos.append((None, propias))
    if opcionales:
        grupos.append((None, opcionales))
    # carpetas que solo contienen el curso opcional (la de Owee) pasan al final
    solo_opcional = lambda g: bool(g[1]) and all(p["opcional"] for p in g[1])   # noqa: E731
    return [g for g in grupos if not solo_opcional(g)] + [g for g in grupos if solo_opcional(g)]


def plan_desde_material(conn, material, perfil_id: int, carpeta_id: int | None = None) -> int:
    """Convierte un archivo ya adjuntado (md, txt, pdf, docx) en un plan de estudio nuevo.
    Si no se reconoce ningún módulo, no deja nada a medias y avisa."""
    plan_id = repo.importar_archivo(conn, material["ruta"], None, perfil_id, None, carpeta_id)
    # sin estructura el lector crea una sola unidad «Contenido importado» con cada línea como tema: no es un plan útil
    unidades = [r["titulo"] for r in conn.execute("SELECT titulo FROM unidades WHERE plan_id=?", (plan_id,))]
    if not unidades or unidades == ["Contenido importado"]:
        repo.borrar_plan(conn, plan_id)
        raise ValueError(t("No encontré módulos ni temas en ese archivo. Revisa que use títulos (#, ##, ###) y listas."))
    return plan_id


def parece_plan(ruta: str) -> bool:
    """¿El archivo tiene estructura de plan (al menos 2 módulos)? Para ofrecer convertirlo."""
    from parsers.file_parser import extract_text
    from parsers.plan_parser import parse_plan
    try:
        return len(parse_plan(extract_text(ruta))["unidades"]) >= 2
    except Exception:
        return False
