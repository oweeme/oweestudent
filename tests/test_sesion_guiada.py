from database import db, repo
from engine import sesion


def _tema():
    c = db.init_db(":memory:")
    p = repo.crear_plan(c, "Máster", 1)
    return c, repo.agregar_tema(c, repo.agregar_unidad(c, p, "U"), "Tema")


def test_los_pasos_se_van_marcando_y_el_siguiente_es_el_primero_pendiente():
    c, tema = _tema()
    assert sesion.estado(c, tema) == [False] * 4 and sesion.siguiente(sesion.estado(c, tema)) == 0
    assert sesion.estado(c, tema, pomodoro_en_marcha=True)[0]                     # un Pomodoro en curso cuenta como paso 1
    repo.registrar_sesion(c, tema, 25)
    assert sesion.estado(c, tema) == [True, False, False, False]
    assert sesion.estado(c, tema, recuerdo_escrito=True)[1]
    repo.crear_tarjeta(c, tema, "¿P?", "R")
    assert sesion.estado(c, tema)[2]
    repo.guardar_nota(c, tema, "lo que recuerdo", 4)
    hechos = sesion.estado(c, tema)
    assert hechos == [True, True, True, True] and sesion.siguiente(hechos) is None


def test_otro_tema_o_sin_tema_empieza_de_cero():
    c, tema = _tema()
    repo.registrar_sesion(c, tema, 25)
    assert sesion.estado(c, None) == [False] * 4
    otro = repo.agregar_tema(c, c.execute("SELECT unidad_id FROM temas").fetchone()[0], "Otro")
    assert sesion.estado(c, otro) == [False] * 4


def test_la_pantalla_estudiar_muestra_los_pasos_y_el_recuerdo_marca_el_segundo():
    import flet as ft
    from ui.state import AppState
    from ui.views import estudio

    class P:
        overlay, platform, width, web = [], ft.PagePlatform.LINUX, 1000, True
        def update(self, *a): pass
        def open(self, x): pass

    st = AppState(P())
    st.conn = db.init_db(":memory:")
    st.plan_id = repo.crear_plan(st.conn, "M", st.perfil_id)
    st.tema_id = repo.agregar_tema(st.conn, repo.agregar_unidad(st.conn, st.plan_id, "U"), "Tema")
    st.tema_titulo = "Tema"
    cuerpo = estudio.build(st)

    def textos(c):
        out, pila = [], [c]
        while pila:
            x = pila.pop()
            if isinstance(x, ft.Text) and x.value:
                out.append(str(x.value))
            for atr in ("controls", "content"):
                h = getattr(x, atr, None)
                pila += list(reversed(h)) if isinstance(h, list) else ([h] if isinstance(h, ft.Control) else [])
        return " ".join(out)
    assert "⬜ 1. Estudia el tema con el Pomodoro" in textos(cuerpo) and "Siguiente: Estudia el tema con el Pomodoro" in textos(cuerpo)
    recuerdo = next(x for x in _controles(cuerpo, ft.TextField) if x.multiline and "Feynman" in x.label)
    recuerdo.value = "lo que recuerdo"
    recuerdo.on_change(None)
    assert "✅ 2. Cierra los apuntes y escribe lo que recuerdas" in textos(cuerpo)


def _controles(c, tipo):
    out, pila = [], [c]
    while pila:
        x = pila.pop()
        if isinstance(x, tipo):
            out.append(x)
        for atr in ("controls", "content"):
            h = getattr(x, atr, None)
            pila += list(reversed(h)) if isinstance(h, list) else ([h] if hasattr(h, "page") else [])
    return out
