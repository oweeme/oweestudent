"""Ajustes según el nivel del perfil: un niño de primaria y un doctorando no estudian igual.

El nivel se elige al crear el perfil (primaria, secundaria, adolescente, universitario, adulto). Cambia cosas
pequeñas pero que importan: cuánto dura un bloque de estudio, qué tan largo es un simulacro, a quién le explicas
(Feynman), cuántas horas propone el asistente y qué funciones se muestran (la gestión de lecturas de
investigación solo aparece a partir de la universidad).
"""

PERFILES = {
    #               (estudio, descanso)  simulacro: (preguntas, minutos)   horas  edad  investigación
    "primaria":      {"pomodoro": (15, 5), "simulacro": (5, 5),   "horas_semana": 3,  "edad": 8,  "investigacion": False},
    "secundaria":    {"pomodoro": (20, 5), "simulacro": (10, 10), "horas_semana": 5,  "edad": 11, "investigacion": False},
    "adolescente":   {"pomodoro": (25, 5), "simulacro": (10, 15), "horas_semana": 6,  "edad": 12, "investigacion": False},
    "universitario": {"pomodoro": (25, 5), "simulacro": (20, 20), "horas_semana": 10, "edad": 12, "investigacion": True},
    "adulto":        {"pomodoro": (25, 5), "simulacro": (20, 20), "horas_semana": 8,  "edad": 12, "investigacion": True},
}
POR_DEFECTO = "universitario"


def ajustes(nivel: str | None) -> dict:
    """Preferencias del nivel (desconocido o vacío = universitario, que es lo que se ha usado siempre)."""
    return PERFILES.get(nivel or "", PERFILES[POR_DEFECTO])


def es_escolar(nivel: str | None) -> bool:
    return (nivel or "") in ("primaria", "secundaria", "adolescente")
