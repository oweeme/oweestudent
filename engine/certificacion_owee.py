"""Preparación para la certificación de Owee: corrección de los simulacros, aprobado o no, y qué tan listo estás.
El certificado oficial lo da un examinador y se registra en el sitio público; esto solo te prepara."""
import json
from urllib.parse import quote

from engine import escritura_owee as motor
from engine import practica
from owee_curso import curso
from owee_curso.examenes import EXAMENES, ORDEN

CORREO = "hector@oweeme.com"
SITIO = "https://oweeme.github.io/owee/"
ENLACES = {"certificacion": SITIO + "certificacion.html", "registro": SITIO + "certificados.html", "examenes": SITIO + "descargas.html",
           "crear_palabras": SITIO + "crear.html"}
MAESTROS = (("maestro_infantil", 300), ("maestro_adultos", 600), ("examinador", 800))     # palabras mínimas del artículo en Owee


def acierta(item: dict, respuesta: str) -> bool:
    """¿La respuesta coincide con alguna de las aceptadas? (sin mayúsculas, espacios ni guiones). Solo ítems con `auto`."""
    r = motor.normalizar(respuesta)
    return bool(r) and any(r == motor.normalizar(a) for a in (item["auto"] or []))


def evaluar(examen_id: str, puntos: dict[str, float]) -> dict:
    """puntos: {id de la parte: puntos obtenidos}. Aplica los criterios oficiales (adultos: 70 % del total y 50 % por parte;
    infantil: «logrado» con el mínimo de puntos de cada parte)."""
    e = EXAMENES[examen_id]
    partes = []
    for p in e["partes"]:
        obtenidos = max(0.0, min(float(puntos.get(p["id"], 0)), p["puntos"]))
        minimo = e["aprobar"]["parte"] if e["ruta"] == "infantil" else e["aprobar"]["parte"] * p["puntos"]
        partes.append({"id": p["id"], "nombre": p["nombre"], "puntos": obtenidos, "maximo": p["puntos"], "pct": obtenidos / p["puntos"],
                       "logrado": obtenidos >= minimo})
    total = sum(x["puntos"] for x in partes)
    maximo = sum(x["maximo"] for x in partes)
    if e["ruta"] == "infantil":
        aprobado = all(x["logrado"] for x in partes)
    else:
        aprobado = total / maximo >= e["aprobar"]["total"] and all(x["logrado"] for x in partes)
    return {"examen": examen_id, "partes": partes, "total": total, "maximo": maximo, "pct": total / maximo, "aprobado": aprobado,
            "flojas": [x["nombre"] for x in partes if not x["logrado"]]}


def guardar(conn, plan_id: int, resultado: dict) -> int:
    return practica.registrar(conn, plan_id, "simulacro", round(resultado["pct"] * 100),
                              {"clase": "examen_owee", "examen": resultado["examen"], "aprobado": resultado["aprobado"],
                               "partes": {x["id"]: x["puntos"] for x in resultado["partes"]}})


def ultimos(conn, plan_id: int) -> dict[str, dict]:
    """El último simulacro de cada examen: {examen: {pct, aprobado, fecha}}."""
    out: dict[str, dict] = {}
    for r in practica.historial(conn, plan_id, "simulacro", limite=200)[::-1]:
        try:
            d = json.loads(r["detalle"] or "{}")
        except ValueError:
            continue
        if d.get("clase") == "examen_owee":
            out[d["examen"]] = {"pct": r["puntaje"], "aprobado": d["aprobado"], "fecha": r["fecha"]}
    return out


def preparacion(conn, plan_id: int, examen_id: str) -> float:
    """Qué parte del curso necesario para ese examen ya marcaste como hecha (niveles 0 hasta el del examen)."""
    nivel = EXAMENES[examen_id]["nivel_curso"]
    hechas = total = 0
    for l in curso.lecciones():
        if l["nivel"] <= nivel:
            total += 1
            hechas += curso.estado_leccion(conn, plan_id, l["id"]) == "completado"
    return hechas / total if total else 0.0


def solicitud_mailto(examen_id: str) -> str:
    """Enlace de correo para pedir el examen oficial (se abre en tu programa de correo; tú lo revisas y lo envías)."""
    titulo = EXAMENES[examen_id]["titulo"]
    cuerpo = f"Quiero presentar el examen: {titulo}.\nEdad: \nPaís: \nNombre: \n"
    return f"mailto:{CORREO}?subject={quote('Idioma Owee: examen de nivel')}&body={quote(cuerpo)}"


def revisar_articulo(texto: str, minimo_palabras: int) -> dict:
    """Lista de comprobación de un artículo para el certificado de maestro/examinador (lo que mira el examinador, sin sustituirlo)."""
    v = motor.valorar(texto)
    compuestos = sorted({w for w in motor._PALABRA.findall(texto or "") if "-" in w and w[0].islower()})
    pasados = any(w.lower() == "pe" for w in motor._PALABRA.findall(texto or ""))
    futuros = any(w.lower() == "pu" for w in motor._PALABRA.findall(texto or ""))
    enlaces = [w for w in ("balo-ke", "pu-le", "te-dure", "ke", "go", "bo") if w in {x.lower() for x in motor._PALABRA.findall(texto or "")}]
    return {"valoracion": v, "minimo": minimo_palabras, "extension_ok": v["palabras"] >= minimo_palabras,
            "sin_errores": not v["invalidas"], "compuestos": compuestos, "pasado": pasados, "futuro": futuros, "enlaces": enlaces,
            "listo": v["palabras"] >= minimo_palabras and not v["invalidas"]}


__all__ = ["EXAMENES", "ORDEN", "acierta", "evaluar", "guardar", "ultimos", "preparacion", "solicitud_mailto", "revisar_articulo"]
