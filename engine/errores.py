"""Diario de errores: qué temas y qué tarjetas te cuestan más, a partir de tus repasos y prácticas.

Estudiar lo que ya sabes se siente bien y rinde poco; lo que más sube el nivel es dedicar el tiempo a lo que fallas.
Todo sale de datos que la app ya guarda (cada repaso con su tarjeta y su nota, y tus prácticas), sin pedirte nada más.
"""
MIN_REPASOS = 3          # menos repasos que esto es ruido: no se juzga un tema ni una tarjeta
FALLO = 2                # nota de repaso ≤ 2 («otra vez») cuenta como fallo


def _base(perfil_id, plan_id):
    sql = """FROM repasos_log r JOIN temas t ON t.id=r.tema_id JOIN unidades u ON u.id=t.unidad_id
             JOIN planes p ON p.id=u.plan_id WHERE p.perfil_id=? AND r.fecha>=date('now','localtime', ?)"""
    return sql, [perfil_id]


def puntos_debiles(conn, perfil_id: int, plan_id: int | None = None, dias: int = 60, limite: int = 8) -> list[dict]:
    """Temas con más fallos: [{tema_id, tema, plan, repasos, fallos, tasa_fallo, practica}] de peor a mejor.
    `practica` = media de tus prácticas de recuperación/Feynman en ese tema (None si no hay)."""
    sql, args = _base(perfil_id, plan_id)
    extra = " AND p.id=?" if plan_id else ""
    filas = conn.execute(f"""SELECT t.id tema_id, t.titulo tema, p.titulo plan, COUNT(*) repasos,
                             SUM(r.calidad<=?) fallos {sql}{extra} GROUP BY t.id""",
                         [FALLO] + args + [f"-{int(dias)} days"] + ([plan_id] if plan_id else [])).fetchall()
    practica = {r["tema_id"]: r["m"] for r in conn.execute(
        "SELECT tema_id, AVG(puntaje) m FROM practicas WHERE tema_id IS NOT NULL AND tipo IN ('recuperacion','feynman') GROUP BY tema_id")}
    out = []
    for f in filas:
        if f["repasos"] < MIN_REPASOS:
            continue
        tasa = f["fallos"] / f["repasos"]
        media = practica.get(f["tema_id"])
        debilidad = tasa if media is None else 0.7 * tasa + 0.3 * (1 - media / 100)
        if debilidad > 0.15:
            out.append({"tema_id": f["tema_id"], "tema": f["tema"], "plan": f["plan"], "repasos": f["repasos"], "fallos": f["fallos"],
                        "tasa_fallo": round(tasa, 2), "practica": None if media is None else round(media), "debilidad": round(debilidad, 2)})
    out.sort(key=lambda d: (-d["debilidad"], -d["repasos"]))
    return out[:limite]


def tarjetas_dificiles(conn, perfil_id: int, plan_id: int | None = None, dias: int = 90, limite: int = 10) -> list[dict]:
    """Tarjetas que más fallas: [{tarjeta_id, pregunta, respuesta, tema, repasos, fallos}], con al menos 2 fallos."""
    sql, args = _base(perfil_id, plan_id)
    extra = " AND p.id=?" if plan_id else ""
    filas = conn.execute(f"""SELECT k.id tarjeta_id, k.pregunta, k.respuesta, t.titulo tema, COUNT(*) repasos, SUM(r.calidad<=?) fallos
                             {sql.replace('FROM repasos_log r', 'FROM repasos_log r JOIN tarjetas k ON k.id=r.tarjeta_id')}{extra}
                             GROUP BY k.id HAVING fallos>=2 ORDER BY fallos DESC, repasos ASC LIMIT ?""",
                         [FALLO] + args + [f"-{int(dias)} days"] + ([plan_id] if plan_id else []) + [limite]).fetchall()
    return [dict(f) for f in filas]


def ids_de_refuerzo(conn, perfil_id: int, plan_id: int | None = None, n: int = 10) -> list[int]:
    """Tarjetas para un refuerzo: primero las que más fallas, luego las de tus temas débiles y las vencidas, sin repetir."""
    ids = [d["tarjeta_id"] for d in tarjetas_dificiles(conn, perfil_id, plan_id, limite=n)]
    for d in puntos_debiles(conn, perfil_id, plan_id):
        if len(ids) >= n:
            break
        ids += [r["id"] for r in conn.execute("SELECT id FROM tarjetas WHERE tema_id=? ORDER BY repeticiones, id", (d["tema_id"],)) if r["id"] not in ids]
    if len(ids) < n:
        sql = """SELECT k.id FROM tarjetas k JOIN temas t ON t.id=k.tema_id JOIN unidades u ON u.id=t.unidad_id JOIN planes p ON p.id=u.plan_id
                 WHERE p.perfil_id=? AND k.proximo_repaso<=date('now','localtime')""" + (" AND p.id=?" if plan_id else "") + " ORDER BY k.proximo_repaso"
        ids += [r["id"] for r in conn.execute(sql, [perfil_id] + ([plan_id] if plan_id else [])) if r["id"] not in ids]
    return ids[:n]
