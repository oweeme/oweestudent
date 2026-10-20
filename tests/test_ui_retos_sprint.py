"""Pantallas de retos y de sprint, y sus tarjetas en «Hoy»."""
import threading
from datetime import date, timedelta

import flet as ft
import pytest

import i18n
from database import db, repo
from engine import ai
from engine import retos as rt
from engine import sprints as sp


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.web, self.abiertos = [], ft.PagePlatform.LINUX, 1000, True, []

    def update(self, *a): pass
    def open(self, x): self.abiertos.append(x)
    def close(self, *a): pass


class _Hilo:
    def __init__(self, target=None, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


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


def _textos(c):
    return " ".join(str(x.value) for x in _todos(c, ft.Text) if x.value)


def _boton(c, texto):
    return next(b for b in _todos(c, (ft.ElevatedButton, ft.OutlinedButton, ft.TextButton)) if texto in str(b.text))


@pytest.fixture
def st(monkeypatch):
    from ui.state import AppState
    monkeypatch.setattr(threading, "Thread", _Hilo)
    s = AppState(_Pagina())
    s.conn = db.init_db(":memory:")
    s.plan_id = repo.crear_plan(s.conn, "Python", s.perfil_id)
    u = repo.agregar_unidad(s.conn, s.plan_id, "U")
    s.t1, s.t2 = repo.agregar_tema(s.conn, u, "Variables"), repo.agregar_tema(s.conn, u, "Funciones")
    return s


@pytest.mark.parametrize("codigo", ["es", "en", "ja"])
def test_retos_crear_cumplir_y_terminar(st, codigo):
    from ui.views import retos
    i18n.fijar_idioma(codigo)
    cuerpo = retos.build(st)
    _boton(cuerpo, "＋").on_click(None)                       # diálogo «Nuevo reto»
    dlg = st.page.abiertos[-1]
    dlg.actions[-1].on_click(None)                             # «Crear» con los valores por defecto
    assert len(rt.retos(st.conn, st.perfil_id)) == 1
    checks = _todos(cuerpo, ft.Checkbox)
    assert len(checks) == 4
    for ch in checks:
        ch.value = True
        ch.on_change(type("E", (), {"control": ch})())
    campo = next(c for c in _todos(cuerpo, ft.TextField) if c.multiline)
    campo.value = "Resolví los ejercicios y aprendí que..."
    terminar = next(b for b in _todos(cuerpo, ft.ElevatedButton) if b.icon == ft.Icons.CHECK)
    terminar.on_click(None)
    assert rt.retos(st.conn, st.perfil_id)[0]["estado"] == "hecho"


def test_retos_no_se_terminan_sin_criterios_ni_evidencia(st):
    from ui.views import retos
    rt.crear_reto(st.conn, st.plan_id, st.t1)
    cuerpo = retos.build(st)
    _todos(cuerpo, ft.ListTile)[0].on_click(None)
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if b.icon == ft.Icons.CHECK).on_click(None)
    assert "marca todos los criterios" in _textos(cuerpo) and rt.retos(st.conn, st.perfil_id)[0]["estado"] == "pendiente"


def test_un_reto_por_cada_tema_desde_la_pantalla(st):
    from ui.views import retos
    cuerpo = retos.build(st)
    _boton(cuerpo, "Un reto por cada tema").on_click(None)
    assert len(rt.retos(st.conn, st.perfil_id)) == 2 and "2 retos creados" in _textos(cuerpo)
    _boton(cuerpo, "Un reto por cada tema").on_click(None)
    assert "ya tienen un reto" in _textos(cuerpo)


def test_reto_con_ia_usa_la_propuesta(st, monkeypatch):
    from ui.views import retos
    monkeypatch.setattr(ai, "ia_disponible", lambda: True)
    monkeypatch.setattr(rt, "proponer_con_ia", lambda tema, ref: {"titulo": "Escribe una función recursiva", "criterios": ["Funciona", "La probé"]})
    cuerpo = retos.build(st)
    _boton(cuerpo, "＋").on_click(None)
    dlg = st.page.abiertos[-1]
    next(s for s in _todos(dlg, ft.Switch) if "IA" in s.label).value = True
    dlg.actions[-1].on_click(None)
    r = rt.retos(st.conn, st.perfil_id)[0]
    assert r["titulo"] == "Escribe una función recursiva" and rt.criterios_de(r) == ["Funciona", "La probé"]


def test_reto_con_ia_que_falla_cae_a_la_plantilla(st, monkeypatch):
    from ui.views import retos
    monkeypatch.setattr(ai, "ia_disponible", lambda: True)

    def falla(tema, ref):
        raise ValueError("no sirvió")
    monkeypatch.setattr(rt, "proponer_con_ia", falla)
    cuerpo = retos.build(st)
    _boton(cuerpo, "＋").on_click(None)
    dlg = st.page.abiertos[-1]
    next(s for s in _todos(dlg, ft.Switch) if "IA" in s.label).value = True
    dlg.actions[-1].on_click(None)
    assert rt.retos(st.conn, st.perfil_id)[0]["titulo"].startswith("Aplica lo aprendido")


@pytest.mark.parametrize("codigo", ["es", "en", "ru", "ja"])
def test_sprint_se_crea_y_muestra_los_siete_pasos(st, codigo):
    from ui.views import sprint
    i18n.fijar_idioma(codigo)
    cuerpo = sprint.build(st)
    _todos(cuerpo, ft.ElevatedButton)[0].on_click(None)       # «Empezar el sprint hoy»
    s = sp.sprint_activo(st.conn, st.perfil_id)
    assert s is not None and len(_todos(cuerpo, ft.Checkbox)) == 7


def test_sprint_marcar_pasos_e_ir_a_la_pantalla_del_paso(st):
    from ui.views import sprint
    sp.crear_sprint(st.conn, st.plan_id, st.t2)
    saltos = []
    cuerpo = sprint.build(st, saltos.append)
    ch = _todos(cuerpo, ft.Checkbox)[0]
    ch.value = True
    ch.on_change(type("E", (), {"control": ch})())
    assert sp.progreso(st.conn, sp.sprint_activo(st.conn, st.perfil_id)["id"])["hechas"] == 1
    botones = [b for b in _todos(cuerpo, ft.TextButton) if b.text == "Ir"]
    assert len(botones) == 6
    botones[0].on_click(None)                                  # el paso 2 (Feynman) abre Práctica en su pestaña
    assert saltos == ["practica"] and st.pestana_practica == 1 and st.tema_id == st.t2
    botones[1].on_click(None)
    assert saltos[-1] == "retos"


def test_practica_abre_la_pestana_que_pide_el_sprint(st):
    from ui.views import practica
    st.pestana_practica = 3
    cuerpo = practica.build(st)
    assert _todos(cuerpo, ft.Tabs)[0].selected_index == 3 and st.pestana_practica is None


def test_sprint_atrasado_lo_avisa(st):
    from ui.views import sprint
    sp.crear_sprint(st.conn, st.plan_id, st.t1, date.today() - timedelta(days=3))
    assert "retraso" in _textos(sprint.build(st))


def test_hoy_muestra_el_paso_del_sprint_y_los_retos_abiertos(st):
    from ui.views import hoy
    sp.crear_sprint(st.conn, st.plan_id, st.t1)
    rt.crear_reto(st.conn, st.plan_id, st.t2)
    saltos = []
    cuerpo = hoy.build(st, lambda: None, lambda: None, ir_sprint=lambda: saltos.append("sprint"), ir_retos=lambda: saltos.append("retos"))
    texto = _textos(cuerpo)
    assert "Tu sprint de 7 días" in texto and "Día 1 · Explorar" in texto and "Retos abiertos" in texto and "Aplica lo aprendido: Funciones" in texto
    _boton(cuerpo, "Abrir el sprint").on_click(None)
    _boton(cuerpo, "Ver todos los retos").on_click(None)
    assert saltos == ["sprint", "retos"]


def test_sin_asignatura_avisan(st):
    from ui.views import retos, sprint
    st.plan_id = None
    assert isinstance(retos.build(st), ft.Text) and isinstance(sprint.build(st), ft.Text)
