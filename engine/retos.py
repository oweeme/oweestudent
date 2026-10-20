"""Retos prácticos: pasar de «lo sé» a «lo sé hacer».

Cada reto tiene un título y unos criterios de éxito que te autoevalúas (una rúbrica sencilla). Se acaba cuando cumples
todos los criterios y escribes tu evidencia: qué hiciste y qué aprendiste. Hay plantillas por tipo de reto y, con IA,
puede proponer uno a partir del material del tema.
"""
import json
from datetime import date

from engine.practica import _secciones
from i18n import marcar, t

TIPOS = ("aplicar", "explicar", "construir", "ensenar", "real", "conversar")
NOMBRES = {"aplicar": marcar("Aplicar con ejercicios o casos"), "explicar": marcar("Explicarlo en voz alta"),
           "construir": marcar("Construir algo pequeño"), "ensenar": marcar("Enseñárselo a alguien"),
           "real": marcar("Usarlo en la vida real"), "conversar": marcar("Hablar o escribir (idiomas)")}


def plantilla(tipo: str, tema: str) -> tuple[str, list[str]]:
    """(título, criterios) del reto de ese tipo para ese tema, en el idioma de la interfaz."""
    if tipo == "aplicar":
        return t("Aplica lo aprendido: {tema}", tema=tema), [
            t("Resolví al menos 3 ejercicios o casos distintos"), t("Lo hice sin mirar mis apuntes primero"),
            t("Revisé mis errores y entendí por qué fallé"), t("Anoté qué haría distinto la próxima vez")]
    if tipo == "explicar":
        return t("Explícalo en voz alta (2 minutos): {tema}", tema=tema), [
            t("Lo expliqué en voz alta o lo grabé"), t("Usé palabras sencillas y un ejemplo"),
            t("No leí mis apuntes mientras explicaba"), t("Pude contestar una pregunta difícil sobre el tema")]
    if tipo == "construir":
        return t("Construye algo con lo aprendido: {tema}", tema=tema), [
            t("Definí un resultado pequeño y concreto"), t("Lo terminé, aunque no sea perfecto"),
            t("Se puede mostrar o probar"), t("Escribí qué aprendí al hacerlo")]
    if tipo == "ensenar":
        return t("Enséñaselo a alguien: {tema}", tema=tema), [
            t("Se lo expliqué a otra persona"), t("Le pedí que me hiciera preguntas"),
            t("Corregí lo que no supe contestar"), t("Anoté qué parte me costó más explicar")]
    if tipo == "real":
        return t("Úsalo en la vida real: {tema}", tema=tema), [
            t("Elegí una situación real donde sirve"), t("Lo usé de verdad en esa situación"),
            t("Comparé el resultado con lo que esperaba"), t("Decidí cómo mejorarlo")]
    if tipo == "conversar":
        return t("Habla o escribe sin traducir: {tema}", tema=tema), [
            t("Hablé o escribí sin traducir palabra por palabra"), t("Usé el vocabulario nuevo del tema"),
            t("Alguien (o la IA) corrigió mis errores"), t("Lo repetí ya corregido")]
    raise ValueError("tipo de reto desconocido")


def crear_reto(conn, plan_id: int, tema_id: int | None, tipo: str = "aplicar", titulo: str | None = None,
               criterios: list[str] | None = None, fecha_limite=None) -> int:
    if tipo not in TIPOS:
        raise ValueError("tipo de reto desconocido")
    tema = ""
    if tema_id:
        r = conn.execute("SELECT titulo FROM temas WHERE id=?", (tema_id,)).fetchone()
        tema = r["titulo"] if r else ""
    tit, crit = plantilla(tipo, tema or t("tu tema"))
    limite = fecha_limite.isoformat() if hasattr(fecha_limite, "isoformat") else (date.fromisoformat(fecha_limite).isoformat() if fecha_limite else None)
    cur = conn.execute("INSERT INTO retos(plan_id,tema_id,tipo,titulo,criterios,fecha_limite) VALUES (?,?,?,?,?,?)",
                       (plan_id, tema_id, tipo, (titulo or tit).strip(), json.dumps([c.strip() for c in (criterios or crit) if c.strip()], ensure_ascii=False), limite))
    conn.commit()
    return cur.lastrowid


def reto(conn, reto_id):
    return conn.execute("""SELECT r.*, t.titulo tema FROM retos r LEFT JOIN temas t ON t.id=r.tema_id WHERE r.id=?""", (reto_id,)).fetchone()


def retos(conn, perfil_id: int, plan_id: int | None = None, estado: str | None = None):
    sql = """SELECT r.*, t.titulo tema, p.titulo plan FROM retos r LEFT JOIN temas t ON t.id=r.tema_id JOIN planes p ON p.id=r.plan_id
             WHERE p.perfil_id=?"""
    args: list = [perfil_id]
    if plan_id:
        sql, args = sql + " AND r.plan_id=?", args + [plan_id]
    if estado:
        sql, args = sql + " AND r.estado=?", args + [estado]
    return conn.execute(sql + " ORDER BY r.estado='hecho', r.id", args).fetchall()


def criterios_de(r) -> list[str]:
    return json.loads(r["criterios"] or "[]")


def cumplidos_de(r) -> list[int]:
    return sorted(set(json.loads(r["cumplidos"] or "[]")))


def progreso(r) -> float:
    total = len(criterios_de(r))
    return len([i for i in cumplidos_de(r) if i < total]) / total if total else 0.0


def marcar_criterio(conn, reto_id: int, indice: int, cumplido: bool):
    r = reto(conn, reto_id)
    if not 0 <= indice < len(criterios_de(r)):
        raise ValueError("criterio inexistente")
    hechos = set(cumplidos_de(r))
    (hechos.add if cumplido else hechos.discard)(indice)
    conn.execute("UPDATE retos SET cumplidos=?, estado='pendiente', hecho_en=NULL WHERE id=?", (json.dumps(sorted(hechos)), reto_id))
    conn.commit()


def agregar_criterio(conn, reto_id: int, texto: str):
    r = reto(conn, reto_id)
    if texto.strip():
        conn.execute("UPDATE retos SET criterios=? WHERE id=?", (json.dumps(criterios_de(r) + [texto.strip()], ensure_ascii=False), reto_id))
        conn.commit()


def guardar_evidencia(conn, reto_id: int, evidencia: str):
    conn.execute("UPDATE retos SET evidencia=? WHERE id=?", (evidencia.strip(), reto_id))
    conn.commit()


def completar(conn, reto_id: int, evidencia: str | None = None) -> bool:
    """Marca el reto como hecho si cumpliste todos los criterios y hay evidencia. Devuelve si se pudo."""
    r = reto(conn, reto_id)
    if evidencia is not None:
        guardar_evidencia(conn, reto_id, evidencia)
        r = reto(conn, reto_id)
    if progreso(r) < 1 or not (r["evidencia"] or "").strip():
        return False
    conn.execute("UPDATE retos SET estado='hecho', hecho_en=date('now','localtime') WHERE id=?", (reto_id,))
    conn.commit()
    return True


def reabrir(conn, reto_id: int):
    conn.execute("UPDATE retos SET estado='pendiente', hecho_en=NULL WHERE id=?", (reto_id,))
    conn.commit()


def borrar(conn, reto_id: int):
    conn.execute("DELETE FROM retos WHERE id=?", (reto_id,))
    conn.commit()


def retos_para_el_plan(conn, plan_id: int, tipo: str = "aplicar", maximo: int = 12) -> int:
    """Un reto por cada tema que todavía no tenga ninguno. Devuelve cuántos creó."""
    n = 0
    for u in conn.execute("SELECT id FROM unidades WHERE plan_id=? ORDER BY orden", (plan_id,)).fetchall():
        for tm in conn.execute("SELECT id FROM temas WHERE unidad_id=? ORDER BY orden", (u["id"],)).fetchall():
            if n >= maximo:
                return n
            if not conn.execute("SELECT 1 FROM retos WHERE tema_id=?", (tm["id"],)).fetchone():
                crear_reto(conn, plan_id, tm["id"], tipo)
                n += 1
    return n


# ---------- con IA ----------
_SIS = ("Eres un tutor que diseña retos prácticos para aplicar lo aprendido. Usas solo el tema y el material dados. "
        "Respondes en el idioma del estudiante, con frases cortas.")


def prompt_reto(tema: str, referencia: str) -> str:
    return (f"TEMA: {tema}\nMATERIAL DEL ESTUDIANTE:\n{referencia[:1800] or '(sin material)'}\n\n"
            "Propón UN reto práctico y concreto para aplicar este tema (no repasar). Responde exactamente así:\n"
            "RETO: una línea con el título\nCRITERIOS:\n- criterio 1\n- criterio 2\n- criterio 3\n- criterio 4\n"
            "Los criterios deben ser comprobables por el propio estudiante (verbos de acción: resolví, construí, expliqué…).")


def proponer_con_ia(tema: str, referencia: str = "", llm=None) -> dict:
    """{titulo, criterios} propuesto por la IA. Lanza ValueError si la respuesta no sirve."""
    if llm is None:
        from engine import ai
        llm = ai._llm
    s = _secciones(llm(prompt_reto(tema, referencia), _SIS, 300), ("RETO", "CRITERIOS"))
    titulo = (s["reto"] or [""])[0].strip()
    criterios = [c for c in s["criterios"] if len(c) > 5][:6]
    if not titulo or len(criterios) < 2:
        raise ValueError(t("La IA no devolvió un reto válido. Reintenta o usa una plantilla."))
    return {"titulo": titulo, "criterios": criterios}
