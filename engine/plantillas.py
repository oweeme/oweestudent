"""Plantillas del asistente de objetivo: de «qué quiero lograr» a un plan de estudio listo para importar.

Cuatro tipos: asignatura (examen), idioma (niveles MCER), tecnología (fundamentos → práctica → proyecto) y posgrado
(pregunta → literatura → método → escritura). Cada plantilla devuelve Markdown con la misma forma que importa el
resto de la app (módulos, temas, entregables y cronograma semanal), así que el reparto de fechas, el progreso, el
Pomodoro y las tarjetas funcionan igual que con un plan importado.

Las plantillas ponen la ESTRUCTURA; no inventan contenido de la materia (ni libros, ni datos): para una asignatura el
temario lo aporta el estudiante. La estructura del Markdown (palabras como «Módulo» o «Temas Clave», los días en
español) es la que entiende el importador y no se traduce; el texto de cada tema sí sale en el idioma de la interfaz.
"""
import math
from dataclasses import dataclass, field
from datetime import date

from i18n import marcar, t
from parsers.plan_parser import parse_plan

TIPOS = ("asignatura", "idioma", "tecnologia", "posgrado")
NOMBRES_TIPO = {"asignatura": marcar("Asignatura o examen"), "idioma": marcar("Idioma"),
                "tecnologia": marcar("Tecnología o habilidad práctica"), "posgrado": marcar("Maestría, doctorado o investigación")}

NIVELES_MCER = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"]
# Horas de estudio guiado acumuladas aproximadas por nivel (orientativas: varían mucho según el idioma y la persona).
HORAS_MCER = {"A0": 0, "A1": 90, "A2": 180, "B1": 350, "B2": 500, "C1": 700, "C2": 1000}
VOCABULARIO_MCER = {"A1": 500, "A2": 1000, "B1": 2000, "B2": 4000, "C1": 8000}      # palabras acumuladas, aprox.
NIVELES_TEC = ("principiante", "intermedio", "avanzado")
ETAPAS = ("inicio", "revision", "escritura")
DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo")   # como se guardan en la base
SEMANAS_POR_MES = 4.345
HORAS_POR_TEMA = 1.5     # lo que asume la app para un tema sin horas propias


@dataclass
class Datos:
    tipo: str
    objetivo: str = ""
    horas_semana: float = 6.0
    meses: int = 6
    nivel_actual: str = ""          # idioma: A0..C1 · tecnología: principiante/intermedio/avanzado
    nivel_meta: str = ""            # idioma: A1..C2
    temario: list[str] = field(default_factory=list)   # asignatura: un tema por línea
    proyecto: str = ""              # tecnología: qué vas a construir
    lecturas_semana: int = 3        # posgrado
    etapa: str = "inicio"           # posgrado: inicio · revision · escritura
    fecha_limite: date | None = None   # examen o entrega final: se añade a «Entregas y exámenes»


# ---------- validación y viabilidad ----------
def validar(d: Datos) -> list[str]:
    """Mensajes (ya traducidos) de lo que falta o no tiene sentido; vacío si se puede generar."""
    e = []
    if d.tipo not in TIPOS:
        return [t("Elige qué quieres lograr.")]
    if not d.objetivo.strip():
        e.append(t("Escribe tu objetivo."))
    if d.horas_semana <= 0 or d.horas_semana > 80:
        e.append(t("Las horas por semana deben estar entre 1 y 80."))
    if d.meses < 1 or d.meses > 60:
        e.append(t("Los meses deben estar entre 1 y 60."))
    if d.tipo == "asignatura" and len([x for x in d.temario if x.strip()]) < 2:
        e.append(t("Pega el temario: un tema por línea (mínimo dos)."))
    if d.tipo == "idioma":
        a, m = NIVELES_MCER.index(d.nivel_actual) if d.nivel_actual in NIVELES_MCER else -1, \
               NIVELES_MCER.index(d.nivel_meta) if d.nivel_meta in NIVELES_MCER else -1
        if a < 0 or m < 1:
            e.append(t("Elige tu nivel actual y el nivel que quieres alcanzar."))
        elif m <= a:
            e.append(t("El nivel que quieres alcanzar debe ser mayor que el actual."))
    return e


def horas_necesarias(d: Datos) -> float:
    """Horas totales que pide el plan (para idiomas, según el MCER; para lo demás, temas × horas por tema)."""
    if d.tipo == "idioma" and d.nivel_actual in HORAS_MCER and d.nivel_meta in HORAS_MCER:
        return float(HORAS_MCER[d.nivel_meta] - HORAS_MCER[d.nivel_actual])
    return len(_temas_de(_estructura(d))) * HORAS_POR_TEMA


def viabilidad(d: Datos) -> dict:
    """¿Alcanza el tiempo? Devuelve horas disponibles, necesarias, y las horas por semana que harían falta."""
    disponibles = d.horas_semana * d.meses * SEMANAS_POR_MES
    necesarias = horas_necesarias(d)
    return {"disponibles": disponibles, "necesarias": necesarias, "ok": disponibles >= necesarias,
            "h_semana_necesarias": necesarias / (d.meses * SEMANAS_POR_MES),
            "meses_necesarios": math.ceil(necesarias / (d.horas_semana * SEMANAS_POR_MES)) if d.horas_semana > 0 else 0}


def mensaje_viabilidad(d: Datos) -> str:
    v = viabilidad(d)
    if v["ok"]:
        return t("Tienes ~{disp:.0f} h y el plan pide ~{nec:.0f} h: te alcanza.", disp=v["disponibles"], nec=v["necesarias"])
    return t("Tienes ~{disp:.0f} h pero el plan pide ~{nec:.0f} h. Necesitarías ~{hs:.1f} h por semana, o unos {meses} meses con tu ritmo.",
             disp=v["disponibles"], nec=v["necesarias"], hs=v["h_semana_necesarias"], meses=v["meses_necesarios"])


# ---------- piezas comunes ----------
def _reparto(pesos: list[float], meses: int) -> list[tuple[int, int]]:
    """Reparte `meses` entre módulos en rangos contiguos (Meses a - b), proporcionales a su peso.
    Si hay más módulos que meses, los módulos comparten mes."""
    total = sum(pesos) or 1
    acum, previo, out = 0.0, 0, []
    for i, p in enumerate(pesos):
        acum += p
        corte = meses if i == len(pesos) - 1 else round(acum / total * meses)
        if corte > previo:
            out.append((previo + 1, corte))
            previo = corte
        else:
            out.append((max(previo, 1), max(previo, 1)))
    return out


def _modulo(n: int, titulo: str, rango: tuple[int, int], temas: list[str], entregable: str | None = None) -> list[str]:
    md = [f"### 🔹 Módulo {n}: {titulo} (Meses {rango[0]} - {rango[1]})", "* **Temas Clave:**", *[f"  * {x}" for x in temas]]
    if entregable:
        md += [f"* **📝 Caso de Estudio Práctico (Tarea {n}):**", f"  * *Entregable:* {entregable}"]
    return md + [""]


def _cronograma(actividades: list[str], horas_semana: float) -> list[str]:
    """Tabla semanal con sesiones de 1 h repartidas de lunes a domingo, de lo más importante a lo menos."""
    n = max(1, min(14, round(horas_semana)))
    sesiones = [actividades[i % len(actividades)] for i in range(n)]
    dias_usados = min(n, 5) if n <= 5 else (n if n < 7 else 7)
    columnas = math.ceil(n / dias_usados)
    cab = "| " + " | ".join([t("Día")] + [t("Bloque {k} (1 h)", k=k + 1) for k in range(columnas)]) + " |"
    filas = ["## 📅 CRONOGRAMA SEMANAL GENERAL", "", cab, "| :--- " + "| :--- " * columnas + "|"]
    for d in range(dias_usados):
        celdas = [sesiones[c * dias_usados + d] if c * dias_usados + d < n else "—" for c in range(columnas)]
        filas.append("| " + " | ".join([f"**{DIAS[d]}**"] + celdas) + " |")
    return filas


def _cabecera(titulo: str, d: Datos) -> list[str]:
    return [f"# {titulo}", f"**Duración Total:** {d.meses} meses", f"**Dedicación:** {d.horas_semana:g} horas semanales", "",
            f"## {t('Tu plan')}", ""]


# ---------- plantillas ----------
def _asignatura(d: Datos):
    temas = [x.strip() for x in d.temario if x.strip()]
    meses_final = max(1, round(d.meses * 0.2)) if d.meses > 1 else 1
    meses_estudio = max(1, d.meses - meses_final) if d.meses > 1 else 1
    por_modulo = 6
    trozos = [temas[i:i + por_modulo] for i in range(0, len(temas), por_modulo)]
    mods = [(t("Parte {n}", n=i + 1), tr, t("Resumen de una página y 10 preguntas de práctica de esta parte")) for i, tr in enumerate(trozos)]
    pesos = [len(tr) for tr in trozos]
    rangos = _reparto(pesos, meses_estudio)
    estructura = [(titulo, rango, tr, ent) for (titulo, tr, ent), rango in zip(mods, rangos)]
    final_ini = meses_estudio if d.meses == 1 else meses_estudio + 1
    estructura.append((t("Repaso final y simulacros"), (min(final_ini, d.meses), d.meses),
                       [t("Repaso general con tarjetas de todo el temario"), t("Simulacro 1 cronometrado"),
                        t("Corregir el simulacro y convertir cada error en una tarjeta"), t("Simulacro 2 cronometrado"),
                        t("Repaso de los puntos débiles y descanso antes de la prueba")], None))
    actividades = [t("Estudio del tema del día"), t("Repaso de tarjetas"), t("Ejercicios y preguntas de práctica"),
                   t("Resumen con tus palabras (Feynman)"), t("Simulacro o repaso de errores")]
    return estructura, actividades


def _idioma(d: Datos):
    a, m = NIVELES_MCER.index(d.nivel_actual), NIVELES_MCER.index(d.nivel_meta)
    niveles = NIVELES_MCER[a + 1:m + 1]
    pesos = [HORAS_MCER[n] - HORAS_MCER[NIVELES_MCER[NIVELES_MCER.index(n) - 1]] for n in niveles]
    rangos = _reparto(pesos, d.meses)
    estructura = []
    for n, rango in zip(niveles, rangos):
        temas = [t("Meta del nivel {n}: {meta}", n=n, meta=_descriptor(n))]
        if n in VOCABULARIO_MCER:
            temas.append(t("Vocabulario: llegar a unas {k} palabras acumuladas (aprox.) con tarjetas", k=VOCABULARIO_MCER[n]))
        temas += [t("Gramática del nivel {n}: reglas y ejercicios", n=n), t("Escucha: 15 minutos al día de audio del nivel"),
                  t("Lectura de textos del nivel {n} con vocabulario nuevo", n=n),
                  t("Escritura: un texto corto por semana, corregido"), t("Conversación: una sesión por semana"),
                  t("Autoevaluación del nivel {n}", n=n)]
        estructura.append((t("{idioma} {n}", idioma=d.objetivo.strip(), n=n), rango, temas,
                           t("Evaluación {n}: grabar una conversación de 5 minutos y escribir un texto de 200 palabras", n=n)))
    actividades = [t("Vocabulario (tarjetas)"), t("Escucha"), t("Lectura"), t("Escritura"), t("Conversación"),
                   t("Gramática"), t("Inmersión libre (series, música, podcasts)")]
    return estructura, actividades


def _descriptor(n: str) -> str:
    return {"A1": t("presentarte, pedir lo básico y entender frases muy sencillas"),
            "A2": t("hablar de rutinas, compras y tu entorno en situaciones simples"),
            "B1": t("desenvolverte en viajes y trabajo, y contar experiencias y planes"),
            "B2": t("conversar con fluidez, entender textos complejos y argumentar tu opinión"),
            "C1": t("usar el idioma con soltura en lo académico y lo profesional"),
            "C2": t("entender casi todo y expresarte con precisión y matices")}[n]


def _tecnologia(d: Datos):
    obj = d.objetivo.strip()
    proyecto = d.proyecto.strip() or t("un proyecto propio de {obj}", obj=obj)
    fases = []
    if d.nivel_actual != "avanzado":
        temas = [t("Instalar y configurar el entorno de {obj}", obj=obj), t("Conceptos básicos y vocabulario de {obj}", obj=obj),
                 t("Primeros ejercicios guiados de {obj}", obj=obj), t("Leer la guía de inicio de la documentación oficial")]
        if d.nivel_actual == "intermedio":
            temas = temas[1:]
        fases.append((t("Fundamentos de {obj}", obj=obj), 2, temas, None))
    fases.append((t("Práctica deliberada"), 3, [t("Ejercicios diarios cortos de {obj}", obj=obj),
                                                t("Reproducir tres tutoriales cambiando algo en cada uno"),
                                                t("Depurar errores y anotar qué aprendiste de cada uno"),
                                                t("Leer código o ejemplos de otras personas")], None))
    fases.append((t("Proyecto: {proyecto}", proyecto=proyecto), 4,
                  [t("Definir el alcance mínimo de {proyecto}", proyecto=proyecto), t("Construir la primera versión que funcione"),
                   t("Probarla, corregirla y mejorarla"), t("Publicarla o mostrarla con una explicación clara")],
                  t("{proyecto} publicado, con una explicación de cómo funciona", proyecto=proyecto)))
    fases.append((t("Consolidación"), 1, [t("Documentar lo aprendido en tus propias palabras"),
                                           t("Revisar qué te costó más y repasarlo"), t("Elegir el siguiente reto")], None))
    rangos = _reparto([f[1] for f in fases], d.meses)
    estructura = [(titulo, rango, temas, ent) for (titulo, _, temas, ent), rango in zip(fases, rangos)]
    actividades = [t("Teoría y documentación"), t("Práctica con ejercicios"), t("Proyecto"), t("Repaso de tarjetas"),
                   t("Depurar y anotar lo aprendido")]
    return estructura, actividades


def _posgrado(d: Datos):
    n = max(1, d.lecturas_semana)
    fases = [
        ("pregunta", t("Pregunta y alcance"), 1, [t("Formular la pregunta de investigación y tres subpreguntas"),
                                                  t("Definir alcance, hipótesis y palabras clave"),
                                                  t("Configurar un gestor de referencias (por ejemplo Zotero)"),
                                                  t("Reunión con tu tutor: validar el alcance")], None),
        ("revision", t("Revisión de literatura"), 3, [t("Búsqueda sistemática: bases de datos y cadenas de búsqueda"),
                                                      t("Cola de lectura: {n} lecturas por semana, con una ficha por texto", n=n),
                                                      t("Mapa de la literatura: agrupar por temas y detectar huecos"),
                                                      t("Resumen crítico de lo que se sabe y lo que falta")],
         t("Mapa de la literatura y resumen crítico")),
        ("metodo", t("Método y datos"), 2, [t("Elegir el método y justificar por qué"), t("Diseñar el estudio o protocolo"),
                                            t("Recolectar o reunir los datos"), t("Análisis preliminar")], t("Protocolo del estudio")),
        ("escritura", t("Escritura"), 4, [t("Esquema de capítulos con meta de palabras por capítulo"),
                                          t("Borrador: introducción y marco teórico"), t("Borrador: método y resultados"),
                                          t("Borrador: discusión y conclusiones"), t("Revisión del borrador con tu tutor")],
         t("Borrador completo")),
        ("cierre", t("Cierre"), 1, [t("Revisar citas y bibliografía"), t("Corregir según los comentarios"),
                                    t("Preparar la presentación o defensa")], None),
    ]
    saltar = {"inicio": 0, "revision": 1, "escritura": 3}.get(d.etapa, 0)
    fases = fases[saltar:]
    rangos = _reparto([f[2] for f in fases], d.meses)
    estructura = [(titulo, rango, temas, ent) for (_, titulo, _, temas, ent), rango in zip(fases, rangos)]
    actividades = [t("Lectura de textos de la cola"), t("Fichas y notas de lectura"), t("Escritura (meta de palabras)"),
                   t("Revisión y reescritura"), t("Seguimiento con tu tutor y planificación")]
    return estructura, actividades


_CONSTRUCTORES = {"asignatura": _asignatura, "idioma": _idioma, "tecnologia": _tecnologia, "posgrado": _posgrado}


def _estructura(d: Datos):
    return _CONSTRUCTORES[d.tipo](d)


def _temas_de(estructura_actividades) -> list[str]:
    estructura, _ = estructura_actividades
    return [x for _, _, temas, _ in estructura for x in temas]


def titulo_plan(d: Datos) -> str:
    if d.tipo == "idioma":
        return t("{idioma}: de {a} a {m}", idioma=d.objetivo.strip(), a=d.nivel_actual, m=d.nivel_meta)
    return d.objetivo.strip()


def generar_markdown(d: Datos) -> str:
    """Plan completo en Markdown listo para `repo.importar_texto`. Lanza ValueError si faltan datos."""
    errores = validar(d)
    if errores:
        raise ValueError(" ".join(errores))
    estructura, actividades = _estructura(d)
    md = _cabecera(titulo_plan(d), d)
    for i, (titulo, rango, temas, ent) in enumerate(estructura, start=1):
        md += _modulo(i, titulo, rango, temas, ent)
    return "\n".join(md + _cronograma(actividades, d.horas_semana)) + "\n"


def resumen(md: str) -> dict:
    """Cuántas unidades y temas tiene el plan generado (para la vista previa)."""
    p = parse_plan(md)
    return {"unidades": [(u["titulo"], len(u["temas"]), u["mes_ini"], u["mes_fin"]) for u in p["unidades"]],
            "temas": sum(len(u["temas"]) for u in p["unidades"]), "cronograma": len(p["cronograma"])}


def crear_plan(conn, d: Datos, perfil_id: int = 1, inicio: date | None = None, carpeta_id: int | None = None) -> int:
    """Genera el plan, lo importa y fija las horas por semana como meta semanal. Devuelve el id del plan."""
    from database import repo
    plan_id = repo.importar_texto(conn, generar_markdown(d), titulo_plan(d), inicio or date.today(), perfil_id, None, carpeta_id)
    conn.execute("UPDATE planes SET horas_semana=? WHERE id=?", (d.horas_semana, plan_id))
    conn.commit()
    if d.fecha_limite:
        if d.tipo == "asignatura":
            repo.agregar_entrega(conn, plan_id, t("Examen: {objetivo}", objetivo=d.objetivo.strip()), d.fecha_limite, "examen")
        else:
            repo.agregar_entrega(conn, plan_id, t("Meta final: {objetivo}", objetivo=d.objetivo.strip()), d.fecha_limite, "proyecto")
    return plan_id
