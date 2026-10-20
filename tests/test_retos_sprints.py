"""Retos prácticos y sprints de 7 días."""
from datetime import date, timedelta

import pytest

import i18n
from database import db, repo
from engine import retos as rt
from engine import sprints as sp
from engine.merge import fusionar


class Con:
    def __init__(self, c, **a):
        self._c = c
        self.__dict__.update(a)

    def __getattr__(self, n):
        return getattr(self._c, n)


@pytest.fixture(autouse=True)
def _es():
    i18n.fijar_idioma("es")
    yield
    i18n.fijar_idioma("es")


@pytest.fixture
def conn():
    c = db.init_db(":memory:")
    plan = repo.crear_plan(c, "Python", 1)
    u = repo.agregar_unidad(c, plan, "Fundamentos")
    t1, t2, t3 = (repo.agregar_tema(c, u, x) for x in ("Variables", "Funciones", "Clases"))
    return Con(c, plan=plan, t1=t1, t2=t2, t3=t3)


def test_plantillas_por_tipo_con_cuatro_criterios():
    for tipo in rt.TIPOS:
        titulo, crit = rt.plantilla(tipo, "Funciones")
        assert "Funciones" in titulo and len(crit) == 4 and all(len(c) > 10 for c in crit), tipo
    with pytest.raises(ValueError):
        rt.plantilla("magia", "x")


def test_crear_y_cumplir_un_reto(conn):
    r = rt.crear_reto(conn, conn.plan, conn.t2, "aplicar")
    fila = rt.reto(conn, r)
    assert fila["titulo"] == "Aplica lo aprendido: Funciones" and fila["tema"] == "Funciones" and rt.progreso(fila) == 0
    assert rt.completar(conn, r, "hice cosas") is False                     # faltan criterios
    for i in range(3):
        rt.marcar_criterio(conn, r, i, True)
    assert rt.progreso(rt.reto(conn, r)) == 0.75 and rt.completar(conn, r, "evidencia") is False
    rt.marcar_criterio(conn, r, 3, True)
    assert rt.completar(conn, r, "   ") is False                              # sin evidencia no vale
    assert rt.completar(conn, r, "Resolví 4 ejercicios de funciones y aprendí a usar return.") is True
    fin = rt.reto(conn, r)
    assert fin["estado"] == "hecho" and fin["hecho_en"] == date.today().isoformat() and "return" in fin["evidencia"]
    rt.marcar_criterio(conn, r, 0, False)                                     # desmarcar reabre el reto
    assert rt.reto(conn, r)["estado"] == "pendiente"


def test_criterios_propios_y_validacion(conn):
    r = rt.crear_reto(conn, conn.plan, None, "construir", titulo="Mi calculadora", criterios=["Suma", "  ", "Resta"])
    assert rt.criterios_de(rt.reto(conn, r)) == ["Suma", "Resta"] and rt.reto(conn, r)["titulo"] == "Mi calculadora"
    rt.agregar_criterio(conn, r, "Multiplica")
    assert len(rt.criterios_de(rt.reto(conn, r))) == 3
    with pytest.raises(ValueError):
        rt.marcar_criterio(conn, r, 9, True)
    with pytest.raises(ValueError):
        rt.crear_reto(conn, conn.plan, None, "otro")
    assert rt.reto(conn, r)["tema"] is None


def test_listado_y_filtros(conn):
    a = rt.crear_reto(conn, conn.plan, conn.t1)
    b = rt.crear_reto(conn, conn.plan, conn.t2, "explicar")
    for i in range(4):
        rt.marcar_criterio(conn, b, i, True)
    rt.completar(conn, b, "listo")
    assert [r["id"] for r in rt.retos(conn, 1)] == [a, b]                     # los hechos al final
    assert [r["id"] for r in rt.retos(conn, 1, estado="pendiente")] == [a] and rt.retos(conn, 1, estado="hecho")[0]["plan"] == "Python"
    assert rt.retos(conn, repo.crear_perfil(conn, "Ana")) == []
    rt.reabrir(conn, b)
    assert rt.reto(conn, b)["estado"] == "pendiente"
    rt.borrar(conn, a)
    assert [r["id"] for r in rt.retos(conn, 1)] == [b]


def test_un_reto_por_tema_sin_repetir(conn):
    assert rt.retos_para_el_plan(conn, conn.plan) == 3
    assert rt.retos_para_el_plan(conn, conn.plan) == 0
    assert rt.retos_para_el_plan(conn, repo.crear_plan(conn, "Vacío", 1)) == 0
    conn.execute("DELETE FROM retos WHERE tema_id=?", (conn.t3,)); conn.commit()
    assert rt.retos_para_el_plan(conn, conn.plan, maximo=1) == 1


def test_propuesta_con_ia(conn):
    visto = []

    def llm(prompt, sistema, tokens):
        visto.append(prompt)
        return "RETO: Escribe una función que ordene una lista\nCRITERIOS:\n- Escribí la función sin copiar\n- Probé con tres listas distintas\n- Expliqué cómo funciona"
    r = rt.proponer_con_ia("Funciones", "def f(): pass", llm)
    assert r["titulo"].startswith("Escribe una función") and len(r["criterios"]) == 3 and "TEMA: Funciones" in visto[0]
    with pytest.raises(ValueError):
        rt.proponer_con_ia("X", "", lambda *a: "no sé")


def test_los_retos_se_sincronizan(tmp_path):
    a, b = db.init_db(str(tmp_path / "a.db")), db.init_db(str(tmp_path / "b.db"))
    p = repo.crear_plan(a, "Tesis", 1)
    r = rt.crear_reto(a, p, None, "ensenar")
    rt.marcar_criterio(a, r, 0, True)
    a.close()
    fusionar(b, str(tmp_path / "a.db"))
    assert rt.progreso(b.execute("SELECT * FROM retos").fetchone()) == 0.25


# ---------- sprints ----------
def test_un_sprint_crea_siete_pasos(conn):
    s = sp.crear_sprint(conn, conn.plan, conn.t2, date(2026, 3, 2))
    ts = sp.tareas(conn, s)
    assert [x["dia"] for x in ts] == list(range(1, 8)) and [x["accion"] for x in ts][:3] == ["material", "feynman", "retos"]
    assert ts[0]["titulo"].startswith("Explorar") and ts[-1]["accion"] == "debiles"
    fila = sp.sprint(conn, s)
    assert fila["titulo"] == "Sprint de 7 días: Funciones" and fila["tema"] == "Funciones" and fila["plan"] == "Python" and fila["estado"] == "activo"


def test_el_dia_de_hoy_y_el_paso_que_toca(conn):
    inicio = date(2026, 3, 2)
    s = sp.sprint(conn, sp.crear_sprint(conn, conn.plan, conn.t1, inicio))
    assert [sp.dia_actual(s, inicio + timedelta(days=d)) for d in (-1, 0, 2, 6, 7, 30)] == [0, 1, 3, 7, 8, 8]
    assert sp.tarea_de_hoy(conn, s, inicio - timedelta(days=1)) is None
    assert sp.tarea_de_hoy(conn, s, inicio)["dia"] == 1 and not sp.va_atrasado(conn, s, inicio)
    assert sp.va_atrasado(conn, s, inicio + timedelta(days=2))                       # el día 3 y no se hizo nada antes
    ts = sp.tareas(conn, s["id"])
    sp.marcar_tarea(conn, ts[0]["id"], True)
    sp.marcar_tarea(conn, ts[1]["id"], True)
    assert sp.tarea_de_hoy(conn, s, inicio + timedelta(days=2))["dia"] == 3 and not sp.va_atrasado(conn, s, inicio + timedelta(days=2))
    sp.marcar_tarea(conn, ts[1]["id"], False)
    assert sp.tarea_de_hoy(conn, s, inicio + timedelta(days=20))["dia"] == 2           # lo primero que falta, aunque pase la semana


def test_el_sprint_termina_al_cumplir_todo_y_se_reabre_si_desmarcas(conn):
    s = sp.crear_sprint(conn, conn.plan, conn.t1)
    for x in sp.tareas(conn, s):
        sp.marcar_tarea(conn, x["id"], True)
    assert sp.sprint(conn, s)["estado"] == "terminado" and sp.progreso(conn, s) == {"hechas": 7, "total": 7, "porcentaje": 100}
    assert sp.sprint_activo(conn, 1) is None
    sp.marcar_tarea(conn, sp.tareas(conn, s)[0]["id"], False)
    assert sp.sprint(conn, s)["estado"] == "activo" and sp.sprint_activo(conn, 1)["id"] == s
    assert sp.tarea_de_hoy(conn, sp.sprint(conn, s))["dia"] == 1


def test_sprint_activo_por_perfil_y_borrado(conn):
    s = sp.crear_sprint(conn, conn.plan, conn.t1)
    ana = repo.crear_perfil(conn, "Ana")
    assert sp.sprint_activo(conn, ana) is None and sp.sprint_activo(conn, 1, conn.plan)["id"] == s
    nuevo = sp.crear_sprint(conn, conn.plan, conn.t2)
    assert sp.sprint_activo(conn, 1)["id"] == nuevo                                       # el más reciente
    sp.borrar(conn, nuevo)
    assert conn.execute("SELECT COUNT(*) FROM sprint_tareas WHERE sprint_id=?", (nuevo,)).fetchone()[0] == 0
    sp.terminar(conn, s)
    assert sp.sprint_activo(conn, 1) is None


def test_los_sprints_se_sincronizan(tmp_path):
    a, b = db.init_db(str(tmp_path / "a.db")), db.init_db(str(tmp_path / "b.db"))
    p = repo.crear_plan(a, "Tesis", 1)
    s = sp.crear_sprint(a, p, None)
    sp.marcar_tarea(a, sp.tareas(a, s)[0]["id"], True)
    a.close()
    fusionar(b, str(tmp_path / "a.db"))
    assert b.execute("SELECT COUNT(*) FROM sprint_tareas").fetchone()[0] == 7 and b.execute("SELECT SUM(hecha) FROM sprint_tareas").fetchone()[0] == 1
