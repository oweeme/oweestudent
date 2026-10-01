"""Ayudas inteligentes.

Offline: reprogramar atrasados y proyección de fin.
Con un modelo local (Ollama, LM Studio…) en este equipo o en otro de tu red: generar planes y tarjetas.
No usa APIs de pago ni sesiones de suscripción.
"""
import json
import os
import re
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

CONFIG = Path(os.environ.get("FLET_APP_STORAGE_DATA") or Path.home() / ".oweestudent") / "config.json"  # fuera de la BD: cada equipo tiene su propia IA


def cargar_config() -> dict:
    try:
        return json.loads(CONFIG.read_text())
    except (OSError, ValueError):
        return {}


def guardar_config(**kw):
    cfg = {**cargar_config(), **kw}
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(cfg))
    CONFIG.chmod(0o600)


# Servidores locales conocidos: (nombre, URL base)
LOCALES = [("Ollama", "http://localhost:11434"), ("LM Studio", "http://localhost:1234"),
           ("llama.cpp", "http://localhost:8080"), ("Jan", "http://localhost:1337")]


def ia_disponible() -> bool:
    cfg = cargar_config()
    return bool((cfg.get("local_url") and cfg.get("local_modelo")) or
                (cfg.get("remoto_url") and cfg.get("remoto_modelo")))


def _http(url, body=None, headers=None, timeout=120):
    req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None,
                                 {"content-type": "application/json", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def modelos_locales(url: str) -> list[str]:
    """Lista modelos de un servidor Ollama (/api/tags) u OpenAI-compatible (/v1/models)."""
    url = url.rstrip("/")
    try:
        return [m["name"] for m in _http(url + "/api/tags", timeout=3)["models"]]
    except Exception:
        return [m["id"] for m in _http(url + "/v1/models", timeout=3)["data"]]


def detectar_local() -> tuple[str, list[str]] | None:
    """Prueba los puertos habituales; devuelve (url, modelos) del primero que responda con modelos."""
    for _, url in LOCALES:
        try:
            ms = modelos_locales(url)
            if ms:
                return url, ms
        except Exception:
            continue
    return None


def _local(prompt, system, max_tokens, url, modelo):
    url = url.rstrip("/")
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    try:  # Ollama nativo
        r = _http(url + "/api/chat", {"model": modelo, "messages": msgs, "stream": False,
                                      "keep_alive": "1m",
                                      "options": {"num_predict": max_tokens, "num_ctx": 2048,
                                                  "temperature": 0.3, "repeat_penalty": 1.2}}, timeout=600)
        return r["message"]["content"]
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
    r = _http(url + "/v1/chat/completions", {"model": modelo, "messages": msgs, "max_tokens": max_tokens,
                                                "temperature": 0.3}, timeout=600)  # LM Studio, llama.cpp, Jan
    return r["choices"][0]["message"]["content"]


def _llm(prompt: str, system: str, max_tokens=4000) -> str:
    """Prueba en orden: IA de este equipo -> IA de otro equipo de la red. Si una falla, pasa a la siguiente."""
    cfg = cargar_config()
    intentos = []
    if cfg.get("local_url") and cfg.get("local_modelo"):
        intentos.append(("este equipo", lambda: _local(prompt, system, max_tokens, cfg["local_url"], cfg["local_modelo"])))
    if cfg.get("remoto_url") and cfg.get("remoto_modelo"):
        intentos.append(("otro equipo", lambda: _local(prompt, system, max_tokens, cfg["remoto_url"], cfg["remoto_modelo"])))
    if not intentos:
        raise RuntimeError("Configura una IA en Ajustes (este equipo u otro de tu red)")
    errores = []
    for nombre, f in intentos:
        try:
            return f()
        except Exception as ex:
            errores.append(f"{nombre}: {ex}")
    raise RuntimeError("Ninguna IA respondió → " + " | ".join(errores))


def buscar_en_red(puerto: int = 11434) -> list[tuple[str, list[str]]]:
    """Busca servidores Ollama en tu red local (mismo /24). Devuelve [(url, modelos)]."""
    import socket
    from concurrent.futures import ThreadPoolExecutor
    from engine.sync import ip_local
    base = ip_local().rsplit(".", 1)[0]

    def sonda(host):
        try:
            with socket.create_connection((host, puerto), timeout=0.4):
                pass
            url = f"http://{host}:{puerto}"
            return url, modelos_locales(url)
        except Exception:
            return None
    with ThreadPoolExecutor(64) as ex:
        return [r for r in ex.map(sonda, [f"{base}.{i}" for i in range(1, 255)]) if r and r[1]]


def _lineas(texto: str, n: int) -> list[str]:
    """Limpia una lista escrita por el modelo: sin numeración, sin repetidos, máx. n líneas."""
    vistos, out = set(), []
    for l in texto.splitlines():
        l = re.sub(r'^[\s*\-•\d.)]+', '', l).replace('**', '').strip(' :')
        k = l.lower()
        if 3 < len(l) < 120 and k not in vistos:
            vistos.add(k)
            out.append(l)
    return out[:n]


def generar_plan(objetivo: str, nivel: str, horas_semana: float, meses: int) -> str:
    """Arma el plan en pasos pequeños (lo que un modelo de 1-2B hace bien) y construye el Markdown en código,
    así el formato siempre es válido. Libros: se añaden a mano (un modelo pequeño los inventa)."""
    sis = "Eres un tutor experto. Responde en español, solo con la lista pedida, una línea por elemento."
    n = max(2, min(6, meses // 2 or 2))
    mods = _lineas(_llm(f"Materia: {objetivo}. Nivel {nivel}.\nLista {n} módulos de ESTA materia, del básico al avanzado. "
                           f"Todos deben tratar específicamente de {objetivo}. Solo títulos cortos.", sis, 150), n)
    if not mods:
        raise RuntimeError("El modelo no devolvió módulos. Reintenta.")
    por_mod = max(1, meses // len(mods))
    md = [f"# {objetivo}", f"**Duración Total:** {meses} meses", f"**Dedicación:** {horas_semana:g} horas semanales", ""]
    for i, m in enumerate(mods):
        m = re.sub(r'^(m[óo]dulo\s*\d+\s*[:.-]\s*)', '', m, flags=re.I)
        temas = _lineas(_llm(f"Materia: {objetivo}. Módulo: {m}.\nLista 5 temas concretos de {objetivo} "
                                "que se estudian en este módulo, sin repetir.", sis, 150), 6)
        ent = _lineas(_llm(f"Propón UN proyecto práctico corto sobre '{m}' dentro de {objetivo}. "
                              "Una sola línea, distinto de otros proyectos.", sis, 60), 1)
        md += [f"### 🔹 Módulo {i + 1}: {m} (Meses {i * por_mod + 1} - {(i + 1) * por_mod})",
               "* **Temas Clave:**", *[f"  * {t}" for t in temas]]
        if ent:
            md += [f"* **📝 Caso de Estudio Práctico (Tarea {i + 1}):**", f"  * *Entregable:* {ent[0]}"]
        md.append("")
    return "\n".join(md)


def tarjetas_desde_material(tema: str, material: str, n: int = 5) -> list[tuple[str, str]]:
    """Preguntas y respuestas basadas SOLO en el material del estudiante (un modelo pequeño acierta mucho más
    cuando la respuesta está en el texto que cuando debe recordar hechos por su cuenta)."""
    txt = _llm(f"Tema: {tema}\nMATERIAL:\n{material[:3000]}\n\nCrea {n} tarjetas de estudio usando SOLO el material. "
                  "Cada respuesta debe copiarse o resumirse del material, sin añadir nada que no esté escrito. "
                  "Sin negritas. Formato exacto, una por bloque:\nP: pregunta\nR: respuesta breve",
                  "Eres un tutor. Usa únicamente la información del material. Responde en español.", 500)
    pares, p = [], None
    for l in txt.replace('**', '').splitlines():
        m = re.match(r'^\s*(?:Tarjeta\s*#?\d+\s*:?\s*)?P\s*\d*\s*[:.)]\s*(.+)', l)
        if m:
            p = m.group(1).strip()
            continue
        m = re.match(r'^\s*R\s*\d*\s*[:.)]\s*(.+)', l)
        if m and p:
            pares.append((p, m.group(1).strip()))
            p = None
    return pares


def resumir_pagina(texto: str) -> str:
    """Resumen en viñetas usando SOLO el texto dado (para leer más rápido; revisa siempre con la fuente)."""
    return _llm(f"TEXTO:\n{texto[:3500]}\n\nResume en 4 a 6 viñetas cortas solo con lo que dice el texto. Sin añadir datos.",
                "Eres un asistente de estudio. Responde en español, con viñetas.", 350)


def preguntas_repaso(tema: str, resumen: str = "") -> str:
    """Genera preguntas para que TÚ compruebes lo que sabes. No juzga si tu resumen es correcto
    (un modelo pequeño se equivoca al verificar hechos)."""
    ctx = f"\nEl estudiante escribió: {resumen}" if resumen.strip() else ""
    return _llm(f"Tema: {tema}.{ctx}\nEscribe 3 preguntas de repaso (una comprensión, una aplicación y una "
                   "de relacionar conceptos). Solo las preguntas, numeradas.",
                   "Eres un tutor. Responde en español, breve.", 200)


# ---------------- Offline ----------------
def reprogramar_atrasados(conn, plan_id: int, por_dia: int = 2, dias_estudio=(0, 1, 2, 3, 4, 5)) -> int:
    """Mueve los temas atrasados (no completados) a los próximos días de estudio, `por_dia` por día."""
    hoy = date.today().isoformat()
    ids = [r["id"] for r in conn.execute(
        """SELECT t.id FROM temas t JOIN unidades u ON u.id=t.unidad_id
           WHERE u.plan_id=? AND t.estado!='completado' AND t.fecha_programada<?
           ORDER BY t.fecha_programada, t.orden""", (plan_id, hoy))]
    d, n = date.today(), 0
    for i, tid in enumerate(ids):
        while d.weekday() not in dias_estudio or n >= por_dia:
            d, n = (d + timedelta(days=1), 0) if n >= por_dia or d.weekday() not in dias_estudio else (d, n)
        conn.execute("UPDATE temas SET fecha_programada=? WHERE id=?", (d.isoformat(), tid))
        n += 1
    conn.commit()
    return len(ids)


def proyeccion(conn, plan_id: int) -> dict | None:
    """Con tu ritmo real de las últimas 4 semanas, ¿cuándo terminas? None si no hay datos."""
    r = conn.execute("""SELECT COUNT(*) n, SUM(t.estado='completado') ok FROM temas t
        JOIN unidades u ON u.id=t.unidad_id WHERE u.plan_id=?""", (plan_id,)).fetchone()
    if not r["n"]:
        return None
    restantes = r["n"] - (r["ok"] or 0)
    h = conn.execute("""SELECT SUM(s.minutos)/60.0 FROM sesiones s JOIN temas t ON t.id=s.tema_id
        JOIN unidades u ON u.id=t.unidad_id WHERE u.plan_id=? AND s.fecha>=date('now','localtime','-27 day')""",
                     (plan_id,)).fetchone()[0] or 0
    h_sem = h / 4
    horas_rest = conn.execute("""SELECT SUM(MAX(t.horas_estimadas-t.horas_dedicadas,0)) FROM temas t
        JOIN unidades u ON u.id=t.unidad_id WHERE u.plan_id=? AND t.estado!='completado'""", (plan_id,)).fetchone()[0] or 0
    fin = date.today() + timedelta(weeks=horas_rest / h_sem) if h_sem > 0.1 else None
    return {"restantes": restantes, "horas_rest": horas_rest, "h_sem": h_sem, "fin": fin}


def prompt_para_chat(objetivo: str, nivel: str, horas_semana: float, meses: int) -> str:
    """Texto para pegar en tu chat de IA favorito (Claude, ChatGPT…, con tu suscripción normal)
    y traer la respuesta a «Importar → texto pegado». Sin APIs."""
    return (f"Diseña un plan de estudio autodidacta sobre: {objetivo}.\nNivel: {nivel}. {horas_semana:g} horas por "
            f"semana durante {meses} meses. Hazlo progresivo, con entregables prácticos y bibliografía real.\n\n"
            "Responde SOLO con Markdown en este formato exacto (sin bloques de código):\n\n"
            f"# Título del plan\n**Duración Total:** {meses} meses\n## SEMESTRE 1: nombre (Meses 1 - {meses})\n"
            "### 🔹 Módulo 1: Nombre (Meses 1 - 2)\n* **Temas Clave:**\n  * tema 1\n  * tema 2\n"
            "* **Bibliografía Principal:**\n  * *Título del libro* – Autor\n"
            "* **📝 Caso de Estudio Práctico (Tarea 1):**\n  * *Entregable:* descripción\n\n"
            "Repite el bloque de módulo para cada módulo.")
