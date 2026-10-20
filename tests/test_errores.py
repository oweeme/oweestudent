"""Diario de errores: temas y tarjetas que más se fallan, y refuerzo."""
import flet as ft
import pytest

from database import db, repo
from engine import errores as er
from engine import practica as pr


@pytest.fixture
def mundo():
    c = db.init_db(":memory:")
    plan = repo.crear_plan(c, "Biología", 1)
    u = repo.agregar_unidad(c, plan, "U")
    dificil, facil = repo.agregar_tema(c, u, "Genética"), repo.agregar_tema(c, u, "Plantas")
    repo.crear_tarjetas(c, dificil, [(f"g{i}?", f"respuesta genética {i}") for i in range(4)], "manual")
    repo.crear_tarjetas(c, facil, [(f"p{i}?", f"respuesta plantas {i}") for i in range(4)], "manual")
    ids = {r["pregunta"]: r["id"] for r in c.execute("SELECT id, pregunta FROM tarjetas")}
    return c, plan, dificil, facil, ids


def repasar(c, tid, notas):
    for n in notas:
        repo.repasar_tarjeta(c, tid, n)


def test_temas_debiles_ordenados_por_fallos(mundo):
    c, plan, dificil, facil, ids = mundo
    repasar(c, ids["g0?"], [1, 1, 4, 0])         # 3 fallos de 4
    repasar(c, ids["g1?"], [1, 4])
    repasar(c, ids["p0?"], [4, 5, 4, 5])         # sin fallos
    d = er.puntos_debiles(c, 1)
    assert [x["tema"] for x in d] == ["Genética"] and d[0]["repasos"] == 6 and d[0]["fallos"] == 4 and d[0]["tasa_fallo"] == 0.67
    assert d[0]["plan"] == "Biología" and d[0]["practica"] is None


def test_con_pocos_repasos_no_se_juzga(mundo):
    c, plan, dificil, facil, ids = mundo
    repasar(c, ids["g0?"], [0, 0])
    assert er.puntos_debiles(c, 1) == []                       # 2 repasos: un tema no se juzga todavía
    assert [x["fallos"] for x in er.tarjetas_dificiles(c, 1)] == [2]       # pero una tarjeta con dos fallos seguidos sí se avisa


def test_la_practica_baja_pesa_en_la_debilidad(mundo):
    c, plan, dificil, facil, ids = mundo
    repasar(c, ids["p0?"], [4, 4, 4, 2])          # un 25 % de fallos: justo por encima del umbral
    solo = er.puntos_debiles(c, 1)
    pr.registrar(c, plan, "recuperacion", 20, {}, facil)
    con = er.puntos_debiles(c, 1)
    assert con[0]["practica"] == 20 and con[0]["debilidad"] > (solo[0]["debilidad"] if solo else 0)


def test_tarjetas_que_mas_se_fallan(mundo):
    c, plan, dificil, facil, ids = mundo
    repasar(c, ids["g0?"], [1, 1, 4])
    repasar(c, ids["g1?"], [1, 4, 4])
    repasar(c, ids["p0?"], [0, 0, 0, 0])
    r = er.tarjetas_dificiles(c, 1)
    assert [x["pregunta"] for x in r] == ["p0?", "g0?"] and r[0]["fallos"] == 4 and r[1]["repasos"] == 3     # g1? solo falló una vez


def test_los_repasos_viejos_no_cuentan(mundo):
    c, plan, dificil, facil, ids = mundo
    repasar(c, ids["g0?"], [1, 1, 1, 1])
    c.execute("UPDATE repasos_log SET fecha=date('now','localtime','-200 days')")
    c.commit()
    assert er.puntos_debiles(c, 1) == [] and er.tarjetas_dificiles(c, 1) == []


def test_alcance_por_asignatura_y_por_perfil(mundo):
    c, plan, dificil, facil, ids = mundo
    repasar(c, ids["g0?"], [1, 1, 1, 4])
    otra = repo.crear_plan(c, "Historia", 1)
    assert er.puntos_debiles(c, 1, otra) == [] and len(er.puntos_debiles(c, 1, plan)) == 1
    ana = repo.crear_perfil(c, "Ana")
    assert er.puntos_debiles(c, ana) == []


def test_ids_de_refuerzo_empiezan_por_lo_que_mas_fallas(mundo):
    c, plan, dificil, facil, ids = mundo
    repasar(c, ids["g0?"], [1, 1, 1, 4])
    repasar(c, ids["g2?"], [1, 1, 4])
    r = er.ids_de_refuerzo(c, 1, plan, 6)
    assert r[:2] == [ids["g0?"], ids["g2?"]] and len(r) == 6 and len(set(r)) == 6
    assert er.ids_de_refuerzo(db.init_db(":memory:"), 1, None, 5) == []


def test_simulacro_de_refuerzo_se_limita_a_esas_tarjetas(mundo):
    c, plan, dificil, facil, ids = mundo
    r = pr.preparar_simulacro(c, 1, plan, n=10, tipo="opciones", semilla=1, ids=[ids["g1?"], ids["g0?"]])
    assert [p.enunciado for p in r] == ["g1?", "g0?"]                       # en el orden dado
    assert all(p.opciones and len(p.opciones) == 4 for p in r)                # los distractores siguen saliendo de todo el alcance


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
        for atr in ("controls", "content", "leading", "trailing", "title", "subtitle", "tabs"):
            h = getattr(x, atr, None)
            if isinstance(h, list):
                pila += reversed(h)
            elif isinstance(h, ft.Control):
                pila.append(h)
    return out


def test_pestana_de_puntos_debiles_y_boton_de_refuerzo(mundo, monkeypatch):
    import threading
    from ui.state import AppState
    from ui.views import practica
    monkeypatch.setattr(threading, "Thread", type("H", (), {"__init__": lambda s, target=None, args=(), daemon=None: setattr(s, "t", target),
                                                            "start": lambda s: s.t() if s.t.__name__ != "cuenta" else None}))
    c, plan, dificil, facil, ids = mundo
    repasar(c, ids["g0?"], [1, 1, 1, 4])
    repasar(c, ids["g1?"], [1, 1, 4])
    st = AppState(_Pagina())
    st.conn, st.plan_id = c, plan
    cuerpo = practica.build(st)
    tabs = _todos(cuerpo, ft.Tabs)[0]
    pestana = tabs.tabs[3].content
    textos = " ".join(str(x.value) for x in _todos(pestana, ft.Text) if x.value)
    assert "Genética" in textos and "fallos" in textos and "g0?" in textos
    next(b for b in _todos(pestana, ft.ElevatedButton) if "refuerzo" in str(b.text)).on_click(None)
    assert tabs.selected_index == 2
    sim = tabs.tabs[2].content
    assert any("Pregunta 1 de" in str(x.value) for x in _todos(sim, ft.Text))


def test_sin_datos_la_pestana_lo_explica(mundo):
    from ui.state import AppState
    from ui.views import practica
    c, plan, *_ = mundo
    st = AppState(_Pagina())
    st.conn, st.plan_id = c, plan
    pestana = _todos(practica.build(st), ft.Tabs)[0].tabs[3].content
    assert "Aún no hay suficientes repasos" in " ".join(str(x.value) for x in _todos(pestana, ft.Text) if x.value)
