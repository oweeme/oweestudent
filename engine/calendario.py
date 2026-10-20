"""Avisos en el calendario del teléfono o del ordenador (archivo .ics).

La app no puede mandar notificaciones por sí sola (Flet no las ofrece todavía en móvil), pero cualquier calendario sí: este archivo
añade tus entregas y exámenes pendientes, cada uno con un aviso el día anterior y otro el mismo día, y un recordatorio DIARIO
a la hora que elijas para repasar tus tarjetas. Importa el archivo en Google Calendar, Apple Calendar, Outlook o el calendario
del sistema y los avisos los da él. Es un archivo: no se envía nada a ningún servidor.
"""
from datetime import date, datetime, timedelta

from database import repo
from i18n import t

PRODID = "-//OweeStudent//Avisos//ES"


def _esc(s: str) -> str:
    """Escapa el texto de un campo .ics: barra, punto y coma, coma y saltos de línea (RFC 5545)."""
    barra = chr(92)
    s = (s or "").replace(barra, barra * 2).replace(";", barra + ";").replace(",", barra + ",")
    return s.replace(chr(13), "").replace(chr(10), barra + "n")


def _doblar(linea: str) -> str:
    """Las líneas de un .ics no pasan de 75 bytes: se continúan en la siguiente con un espacio (RFC 5545)."""
    datos, partes = linea.encode("utf-8"), []
    while len(datos) > 75:
        corte = 75
        while corte > 0 and (datos[corte] & 0xC0) == 0x80:      # no cortar un carácter UTF-8 por la mitad
            corte -= 1
        partes.append(datos[:corte].decode("utf-8"))
        datos = b" " + datos[corte:]
    partes.append(datos.decode("utf-8"))
    return "\r\n".join(partes)


def _alarma(disparo: str, texto: str) -> list[str]:
    return ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{_esc(texto)}", f"TRIGGER:{disparo}", "END:VALARM"]


def crear_ics(conn, perfil_id: int, hora_repaso: str | None = "19:00", ahora: datetime | None = None) -> str:
    """Texto del .ics con las entregas pendientes y (si `hora_repaso`, «HH:MM») un recordatorio diario de repaso."""
    ahora = ahora or datetime.now()
    sello = ahora.strftime("%Y%m%dT%H%M%S")
    ls = ["BEGIN:VCALENDAR", "VERSION:2.0", f"PRODID:{PRODID}", "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]
    nombres = {"tarea": t("Tarea"), "examen": t("Examen"), "proyecto": t("Proyecto"), "otro": t("Otro")}
    for e in repo.entregas(conn, perfil_id, estado="pendiente"):
        dia = date.fromisoformat(e["fecha"])
        ls += ["BEGIN:VEVENT", f"UID:entrega-{e['id']}@oweestudent", f"DTSTAMP:{sello}", f"DTSTART;VALUE=DATE:{dia:%Y%m%d}",
               f"DTEND;VALUE=DATE:{dia + timedelta(days=1):%Y%m%d}", f"SUMMARY:{_esc(nombres.get(e['tipo'], '') + ': ' + e['titulo'])}",
               f"DESCRIPTION:{_esc((e['plan'] or '') + ('. ' + e['detalle'] if e['detalle'] else ''))}", "TRANSP:TRANSPARENT"]
        ls += _alarma("-P1D", t("Mañana: {titulo}", titulo=e["titulo"]))
        ls += _alarma("-PT0S", t("Hoy: {titulo}", titulo=e["titulo"]))
        ls.append("END:VEVENT")
    if hora_repaso:
        h, m = (int(x) for x in hora_repaso.split(":"))
        if not (0 <= h < 24 and 0 <= m < 60):
            raise ValueError("hora inválida")
        inicio = datetime.combine(ahora.date(), datetime.min.time()).replace(hour=h, minute=m)
        ls += ["BEGIN:VEVENT", "UID:repaso-diario@oweestudent", f"DTSTAMP:{sello}", f"DTSTART:{inicio:%Y%m%dT%H%M%S}", "DURATION:PT15M",
               "RRULE:FREQ=DAILY", f"SUMMARY:{_esc(t('Repaso diario en OweeStudent'))}", f"DESCRIPTION:{_esc(t('Abre OweeStudent y repasa tus tarjetas.'))}"]
        ls += _alarma("-PT0S", t("Repaso diario en OweeStudent"))
        ls.append("END:VEVENT")
    ls.append("END:VCALENDAR")
    return "\r\n".join(_doblar(x) for x in ls) + "\r\n"


def validar_hora(texto: str) -> bool:
    try:
        h, m = (int(x) for x in texto.strip().split(":"))
        return 0 <= h < 24 and 0 <= m < 60
    except ValueError:
        return False
