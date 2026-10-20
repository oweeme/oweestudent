"""Avisos en el calendario (.ics)."""
from datetime import date, datetime

import flet as ft
import pytest
from conftest import Con

from database import db, repo
from engine import calendario as cal


@pytest.fixture
def conn():
    c = db.init_db(":memory:")
    plan = repo.crear_plan(c, "Matemática; álgebra, y más", 1)
    repo.agregar_entrega(c, plan, "Examen de álgebra", date(2026, 11, 3), "examen", "Capítulos 1-4\nTraer calculadora")
    repo.agregar_entrega(c, plan, "Tarea; fracciones, decimales", date(2026, 10, 25))
    hecha = repo.agregar_entrega(c, plan, "Ya entregada", date(2026, 10, 20))
    repo.marcar_entrega(c, hecha, True)
    return Con(c, plan=plan)


AHORA = datetime(2026, 10, 19, 9, 30)


def test_estructura_basica_con_saltos_crlf(conn):
    ics = cal.crear_ics(conn, 1, "19:00", AHORA)
    assert ics.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n") and ics.endswith("END:VCALENDAR\r\n") and "\n" not in ics.replace("\r\n", "")
    assert ics.count("BEGIN:VEVENT") == ics.count("END:VEVENT") == 3          # dos entregas pendientes + el repaso diario
    assert "Ya entregada" not in ics                                            # lo hecho no avisa


def test_cada_entrega_avisa_el_dia_antes_y_el_mismo_dia(conn):
    ics = cal.crear_ics(conn, 1, None, AHORA)
    assert ics.count("BEGIN:VALARM") == 4 and ics.count("TRIGGER:-P1D") == 2 and ics.count("TRIGGER:-PT0S") == 2
    assert "DTSTART;VALUE=DATE:20261103" in ics and "DTEND;VALUE=DATE:20261104" in ics and "SUMMARY:Examen: Examen de álgebra" in ics
    assert "repaso-diario" not in ics and "UID:entrega-1@oweestudent" in ics


def test_los_textos_se_escapan(conn):
    b = chr(92)                                                                # la barra invertida de escape
    ics = cal.crear_ics(conn, 1, None, AHORA).replace("\r\n ", "")           # (después de desdoblar las líneas largas)
    assert f"SUMMARY:Tarea: Tarea{b};" in ics and f"fracciones{b}, decimales" in ics
    assert f"Matemática{b}; álgebra{b}, y más. Capítulos 1-4{b}nTraer calculadora" in ics


def test_recordatorio_diario_de_repaso(conn):
    ics = cal.crear_ics(conn, 1, "07:45", AHORA)
    assert "DTSTART:20261019T074500" in ics and "RRULE:FREQ=DAILY" in ics and "DURATION:PT15M" in ics and "UID:repaso-diario@oweestudent" in ics
    with pytest.raises(ValueError):
        cal.crear_ics(conn, 1, "25:00", AHORA)
    assert [cal.validar_hora(x) for x in ("19:00", "7:5", "24:00", "ab", "", "12:60")] == [True, True, False, False, False, False]


def test_ninguna_linea_pasa_de_75_bytes_ni_corta_un_caracter(conn):
    larga = "Entrega con un título larguísimo con acentos áéíóú ñ y emojis 🎓 " * 4
    repo.agregar_entrega(conn, conn.plan, larga, date(2026, 12, 1))
    ics = cal.crear_ics(conn, 1, None, AHORA)
    assert all(len(linea.encode("utf-8")) <= 75 for linea in ics.split("\r\n"))
    assert "🎓" in ics.replace("\r\n ", "")                                      # al desdoblar, el texto está completo


def test_lo_lee_una_biblioteca_de_calendarios_real(conn):
    icalendar = pytest.importorskip("icalendar")
    cal_ = icalendar.Calendar.from_ical(cal.crear_ics(conn, 1, "19:00", AHORA).encode("utf-8"))
    eventos = [c for c in cal_.walk("VEVENT")]
    assert len(eventos) == 3
    examen = next(e for e in eventos if "álgebra" in str(e["SUMMARY"]))
    assert examen["DTSTART"].dt == date(2026, 11, 3) and len(examen.subcomponents) == 2
    assert {str(a["TRIGGER"].dt) for a in examen.subcomponents} == {"-1 day, 0:00:00", "0:00:00"}
    diario = next(e for e in eventos if "repaso-diario" in str(e["UID"]))
    assert diario["RRULE"]["FREQ"] == ["DAILY"] and diario["DTSTART"].dt == datetime(2026, 10, 19, 19, 0)


def test_por_perfil(conn):
    ana = repo.crear_perfil(conn, "Ana")
    assert cal.crear_ics(conn, ana, None, AHORA).count("BEGIN:VEVENT") == 0


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.web = [], ft.PagePlatform.LINUX, 1000, True

    def update(self, *a): pass
    def open(self, x): pass
    def close(self, *a): pass


def _todos(control, tipo):
    out, pila = [], [control]
    while pila:
        x = pila.pop()
        if isinstance(x, tipo):
            out.append(x)
        for atr in ("controls", "content", "leading", "trailing", "title", "subtitle"):
            h = getattr(x, atr, None)
            if isinstance(h, list):
                pila += reversed(h)
            elif isinstance(h, ft.Control):
                pila.append(h)
    return out


def test_la_pantalla_guarda_el_archivo_y_valida_la_hora(conn):
    from database.db import DATOS
    from ui.state import AppState
    from ui.views import entregas
    st = AppState(_Pagina())
    st.conn, st.plan_id = conn, conn.plan
    cuerpo = entregas.build(st)
    boton = next(b for b in _todos(cuerpo, ft.OutlinedButton) if "calendario" in str(b.text))
    hora = next(x for x in _todos(cuerpo, ft.TextField) if "recordatorio diario" in (x.label or ""))
    hora.value = "tarde"
    boton.on_click(None)
    assert "formato HH:MM" in " ".join(str(x.value) for x in _todos(cuerpo, ft.Text) if x.value)
    hora.value = "18:30"
    boton.on_click(None)
    ruta = next(x.value for x in _todos(cuerpo, ft.Text) if "Guardado en" in str(x.value)).split(": ", 1)[1].split(". ")[0]
    assert ruta.endswith(".ics") and str(DATOS) in ruta and "T183000" in open(ruta, encoding="utf-8", newline="").read()
