"""La sesión de estudio guiada: cuatro pasos que se sabe que funcionan (estudiar, recordar sin mirar, crear tarjetas, programar el repaso)."""
from i18n import marcar

PASOS = (marcar("Estudia el tema con el Pomodoro"), marcar("Cierra los apuntes y escribe lo que recuerdas"),
         marcar("Crea tarjetas con lo importante"), marcar("Puntúa cómo lo recordaste y programa el repaso"))


def estado(conn, tema_id, pomodoro_en_marcha: bool = False, recuerdo_escrito: bool = False) -> list[bool]:
    """Qué pasos de hoy ya están hechos para ese tema."""
    if not tema_id:
        return [False] * 4
    estudio = conn.execute("SELECT 1 FROM sesiones WHERE tema_id=? AND fecha=date('now','localtime') LIMIT 1", (tema_id,)).fetchone() is not None
    tarjetas = conn.execute("SELECT 1 FROM tarjetas WHERE tema_id=? AND date(creado,'localtime')=date('now','localtime') LIMIT 1", (tema_id,)).fetchone() is not None
    repaso = conn.execute("SELECT 1 FROM notas WHERE tema_id=? AND date(creado,'localtime')=date('now','localtime') LIMIT 1", (tema_id,)).fetchone() is not None
    return [estudio or pomodoro_en_marcha, recuerdo_escrito or repaso, tarjetas, repaso]


def siguiente(hechos: list[bool]) -> int | None:
    """Índice del primer paso pendiente (None si ya terminaste los cuatro)."""
    return next((i for i, h in enumerate(hechos) if not h), None)
