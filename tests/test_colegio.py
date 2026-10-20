"""Estudiantes de colegio: ajustes por nivel, entregas y exámenes, y su efecto en las pantallas."""
from datetime import date, timedelta

import flet as ft
import pytest

import i18n
from database import db, repo
from engine import nivel, plantillas as pl
from conftest import Con
from engine.merge import fusionar


@pytest.fixture
def conn():
    c = db.init_db(":memory:")
    return Con(c, plan=repo.crear_plan(c, "Matemática", 1))


def dia(dias=0):
    return (date.today() + timedelta(days=dias)).isoformat()


def test_ajustes_por_nivel():
    assert nivel.ajustes("primaria")["pomodoro"] == (15, 5) and nivel.ajustes("universitario")["pomodoro"] == (25, 5)
    assert nivel.ajustes("primaria")["investigacion"] is False and nivel.ajustes("adulto")["investigacion"] is True
    assert nivel.ajustes(None) == nivel.ajustes("universitario") == nivel.ajustes("algo raro")
    assert nivel.es_escolar("secundaria") and not nivel.es_escolar("universitario") and not nivel.es_escolar(None)
    for n, p in nivel.PERFILES.items():
        assert p["pomodoro"][0] > p["pomodoro"][1] > 0 and p["simulacro"][0] >= 5 and p["edad"] >= 8, n


def test_entregas_dias_restantes_y_orden(conn):
    a = repo.agregar_entrega(conn, conn.plan, "Examen de álgebra", dia(3), "examen")
    b = repo.agregar_entrega(conn, conn.plan, "Tarea de fracciones", dia(-2))
    c = repo.agregar_entrega(conn, conn.plan, "Proyecto de feria", dia(20), "proyecto", "Maqueta")
    filas = repo.entregas(conn, 1)
    assert [f["titulo"] for f in filas] == ["Tarea de fracciones", "Examen de álgebra", "Proyecto de feria"]
    assert [f["dias"] for f in filas] == [-2, 3, 20] and filas[0]["plan"] == "Matemática"
    assert [e["titulo"] for e in repo.proximas_entregas(conn, 1, 7)] == ["Tarea de fracciones", "Examen de álgebra"]   # la vencida también
    repo.marcar_entrega(conn, b, True, nota=8.5)
    assert [e["titulo"] for e in repo.proximas_entregas(conn, 1, 7)] == ["Examen de álgebra"]
    assert repo.entregas(conn, 1)[-1]["estado"] == "hecha" and repo.entregas(conn, 1)[-1]["nota"] == 8.5     # las hechas, al final
    repo.editar_entrega(conn, a, fecha=dia(1), titulo="Examen de álgebra (final)")
    assert repo.entregas(conn, 1, estado="pendiente")[0]["dias"] == 1
    repo.borrar_entrega(conn, c)
    assert len(repo.entregas(conn, 1)) == 2


def test_entregas_validan_tipo_y_fecha(conn):
    with pytest.raises(ValueError):
        repo.agregar_entrega(conn, conn.plan, "x", dia(), "tipo-raro")
    with pytest.raises(ValueError):
        repo.agregar_entrega(conn, conn.plan, "x", "mañana")
    with pytest.raises(ValueError):
        repo.editar_entrega(conn, repo.agregar_entrega(conn, conn.plan, "x", dia()), tipo="raro")


def test_entregas_son_de_cada_perfil_y_se_borran_con_la_asignatura(conn):
    otro = repo.crear_perfil(conn, "Ana", "primaria")
    pa = repo.crear_plan(conn, "Lengua", otro)
    repo.agregar_entrega(conn, pa, "Dictado", dia(1))
    repo.agregar_entrega(conn, conn.plan, "Mía", dia(1))
    assert [e["titulo"] for e in repo.entregas(conn, otro)] == ["Dictado"] and [e["titulo"] for e in repo.entregas(conn, 1)] == ["Mía"]
    repo.borrar_plan(conn, pa)
    assert repo.entregas(conn, otro) == []


def test_las_entregas_se_sincronizan(tmp_path):
    a, b = db.init_db(str(tmp_path / "a.db")), db.init_db(str(tmp_path / "b.db"))
    p = repo.crear_plan(a, "Historia", 1)
    e = repo.agregar_entrega(a, p, "Línea de tiempo", dia(4))
    a.close()
    fusionar(b, str(tmp_path / "a.db"))
    assert b.execute("SELECT titulo, tipo FROM entregas").fetchone()[:] == ("Línea de tiempo", "tarea")
    repo.marcar_entrega(b, b.execute("SELECT id FROM entregas").fetchone()[0], True)
    b.close()
    a = db.init_db(str(tmp_path / "a.db"))
    fusionar(a, str(tmp_path / "b.db"))
    assert a.execute("SELECT estado FROM entregas WHERE id=?", (e,)).fetchone()[0] == "hecha"


def test_el_asistente_crea_el_examen_con_su_fecha(conn):
    d = pl.Datos("asignatura", "Cálculo I", 6, 2, temario=["Límites", "Derivadas", "Integrales"], fecha_limite=date.today() + timedelta(days=60))
    p = pl.crear_plan(conn, d, 1)
    e = repo.entregas(conn, 1, p)[0]
    assert e["tipo"] == "examen" and e["titulo"] == "Examen: Cálculo I" and e["dias"] == 60
    q = pl.crear_plan(conn, pl.Datos("tecnologia", "Python", 4, 3, "principiante", fecha_limite=date.today() + timedelta(days=90)), 1)
    assert repo.entregas(conn, 1, q)[0]["tipo"] == "proyecto"
    r = pl.crear_plan(conn, pl.Datos("idioma", "Inglés", 4, 6, "A0", "A2"), 1)
    assert repo.entregas(conn, 1, r) == []


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.web = [], ft.PagePlatform.LINUX, 1000, True
        self.abiertos = []

    def update(self, *a): pass
    def open(self, x): self.abiertos.append(x)
    def close(self, *a): pass
    def set_clipboard(self, x): pass


@pytest.fixture
def st(conn):
    from ui.state import AppState
    s = AppState(_Pagina())
    s.conn = conn
    s.plan_id = conn.plan
    return s


def _todos(control, tipo):
    out, pila = [], [control]
    while pila:
        x = pila.pop()
        if isinstance(x, tipo):
            out.append(x)
        for atr in ("controls", "content", "leading", "trailing", "title", "subtitle", "tabs"):
            h = getattr(x, atr, None)
            if isinstance(h, list):
                pila += reversed(h)
            elif isinstance(h, ft.Control):
                pila.append(h)
    return out


def _textos(control):
    return " ".join(str(x.value) for x in _todos(control, ft.Text) if x.value)


def test_el_nivel_del_perfil_llega_a_la_aplicacion(st):
    assert st.nivel() == "universitario"
    nuevo = repo.crear_perfil(st.conn, "Luis", "primaria")
    st.elegir_perfil(nuevo)
    assert st.nivel() == "primaria"


def test_pomodoro_corto_para_primaria(st):
    from ui.views import estudio
    assert "25:00" in _textos(estudio.build(st))
    st.elegir_perfil(repo.crear_perfil(st.conn, "Luis", "primaria"))
    assert "15:00" in _textos(estudio.build(st))


def test_simulacro_y_feynman_se_adaptan_al_nivel(st):
    from ui.views import practica
    st.elegir_perfil(repo.crear_perfil(st.conn, "Luis", "primaria"))
    st.plan_id = repo.crear_plan(st.conn, "Ciencias", st.perfil_id)
    u = repo.agregar_unidad(st.conn, st.plan_id, "U")
    repo.agregar_tema(st.conn, u, "Plantas")
    cuerpo = practica.build(st)
    valores = {d.label: d.value for d in _todos(cuerpo, ft.Dropdown)}
    assert valores["Preguntas"] == "5" and valores["Tiempo"] == "5"
    assert any("alguien de 8 años" in (c.label or "") for c in _todos(cuerpo, ft.TextField))


def test_el_asistente_propone_menos_horas_a_un_nino(st):
    from ui.views import asistente
    st.elegir_perfil(repo.crear_perfil(st.conn, "Luis", "primaria"))
    cuerpo = asistente.build(st, lambda: None)
    next(c for c in _todos(cuerpo, ft.RadioGroup)).on_change(type("E", (), {"control": type("C", (), {"value": "idioma"})()})())
    horas = next(c for c in _todos(cuerpo, ft.TextField) if c.label == "Horas/semana")
    assert horas.value == "3"


@pytest.mark.parametrize("codigo", ["es", "en", "ru", "ja"])
def test_pantalla_de_entregas(st, codigo):
    from ui.views import entregas
    i18n.fijar_idioma(codigo)
    try:
        repo.agregar_entrega(st.conn, st.plan_id, "Examen de álgebra", dia(1), "examen")
        repo.agregar_entrega(st.conn, st.plan_id, "Tarea", dia(-1))
        cuerpo = entregas.build(st)
        assert len(_todos(cuerpo, ft.ListTile)) == 2
        _todos(cuerpo, ft.Checkbox)[0].on_change(type("E", (), {"control": type("C", (), {"value": True})()})())   # marca la vencida
    finally:
        i18n.fijar_idioma("es")
    assert repo.entregas(st.conn, 1, estado="hecha")[0]["titulo"] == "Tarea"


def test_cuando_en_palabras():
    from ui.views.entregas import cuando
    assert [cuando(d) for d in (0, 1, 5, -1, -3)] == ["hoy", "mañana", "en 5 días", "hace 1 día", "hace 3 días"]
    i18n.fijar_idioma("en")
    try:
        assert cuando(1) == "tomorrow" and cuando(-1) == "1 day ago" and cuando(-3) == "3 days ago"
    finally:
        i18n.fijar_idioma("es")


def test_hoy_muestra_lo_proximo(st):
    from ui.views import hoy as vista_hoy
    repo.agregar_entrega(st.conn, st.plan_id, "Examen de álgebra", dia(2), "examen")
    repo.agregar_entrega(st.conn, st.plan_id, "Proyecto lejano", dia(40), "proyecto")
    texto = _textos(vista_hoy.build(st, lambda: None, lambda: None))
    assert "Examen de álgebra" in texto and "en 2 días" in texto and "Proyecto lejano" not in texto
