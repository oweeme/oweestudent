"""Tu estudio propio va primero; el curso de Owee es opcional."""
import flet as ft
import pytest

from database import db, repo
from owee_curso import curso
from ui.state import AppState


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
        for atr in ("controls", "content", "leading", "trailing", "title", "subtitle", "items"):
            h = getattr(x, atr, None)
            if isinstance(h, list):
                pila += reversed(h)
            elif isinstance(h, ft.Control):
                pila.append(h)
    return out


def _textos(c):
    return " ".join(str(x.value) for x in _todos(c, ft.Text) if x.value)


@pytest.fixture
def st():
    s = AppState(_Pagina())
    s.conn = db.init_db(":memory:")
    s.plan_id = None
    return s


def test_el_curso_de_owee_nunca_le_quita_el_primer_lugar_a_tu_estudio(st):
    propio = repo.crear_plan(st.conn, "Global Master", st.perfil_id)
    curso.crear_plan_del_curso(st.conn, st.perfil_id)              # se añade DESPUÉS: es el más reciente
    st.elegir_perfil(st.perfil_id)
    assert st.plan_id == propio
    assert AppState.plan_por_defecto(repo.planes(st.conn, st.perfil_id)) == propio


def test_si_solo_hay_curso_se_abre_el_curso_y_si_no_hay_nada_no_hay_plan(st):
    assert AppState.plan_por_defecto([]) is None
    p = curso.crear_plan_del_curso(st.conn, st.perfil_id)
    assert AppState.plan_por_defecto(repo.planes(st.conn, st.perfil_id)) == p


def test_de_varios_propios_gana_el_mas_reciente(st):
    repo.crear_plan(st.conn, "Viejo", st.perfil_id)
    nuevo = repo.crear_plan(st.conn, "Nuevo", st.perfil_id)
    curso.crear_plan_del_curso(st.conn, st.perfil_id)
    assert AppState.plan_por_defecto(repo.planes(st.conn, st.perfil_id)) == nuevo


def test_borrar_el_plan_activo_no_pasa_al_curso_si_queda_algo_tuyo(st):
    from ui.views import estudios
    a = repo.crear_plan(st.conn, "A", st.perfil_id)
    b = repo.crear_plan(st.conn, "B", st.perfil_id)
    curso.crear_plan_del_curso(st.conn, st.perfil_id)
    st.plan_id = b
    cuerpo = estudios.build(st, lambda pid: None, lambda *a: None, lambda: None)
    tarjeta_b = next(x for x in _todos(cuerpo, ft.Container) if isinstance(x.content, ft.Column)
                     and getattr(x.content.controls[0].controls[0], "value", None) == "B")
    menu = next(m for m in _todos(tarjeta_b, ft.PopupMenuButton))
    item = next(i for i in menu.items if i.text == "Borrar")
    st.page.open = lambda dlg: setattr(st, "dlg", dlg)
    item.on_click(None)
    st.dlg.actions[-1].on_click(None)
    assert st.plan_id == a                                 # pasa a «A», no al curso (que es el más reciente)
    assert repo.planes(st.conn, st.perfil_id)[0]["titulo"] == "Aprende Owee"


def test_hoy_sin_estudio_propio_guia_primero_a_lo_tuyo_y_ofrece_owee(st):
    from ui.views import hoy
    saltos = []
    cuerpo = hoy.build(st, lambda: None, lambda: None, ir_asistente=lambda: saltos.append("asistente"), ir_importar=lambda: saltos.append("importar"),
                       ir_owee=lambda: saltos.append("owee"))
    texto = _textos(cuerpo)
    assert "Empieza aquí" in texto and "Aprende Owee (opcional)" in texto and "tu propio estudio va primero" in texto
    botones = {b.text: b for b in _todos(cuerpo, (ft.ElevatedButton, ft.OutlinedButton))}
    botones["Crear mi plan con el asistente"].on_click(None)
    botones["Importar un plan que ya tengo"].on_click(None)
    botones["Empezar el curso"].on_click(None)
    assert saltos == ["asistente", "importar", "owee"]
    assert "Esta semana" not in texto                                     # nada de tarjetas vacías de un plan que no existe


def test_hoy_con_solo_el_curso_sigue_pidiendo_tu_estudio_pero_continua_la_leccion(st):
    from ui.views import hoy
    p = curso.crear_plan_del_curso(st.conn, st.perfil_id)
    curso.marcar_leccion(st.conn, p, "0.1", True)
    st.plan_id = p
    cuerpo = hoy.build(st, lambda: None, lambda: None)
    assert "Empieza aquí" in _textos(cuerpo)
    assert any(str(b.text).startswith("Continuar: lección 0.2") for b in _todos(cuerpo, ft.ElevatedButton))


def test_hoy_con_estudio_propio_no_estorba_con_owee_salvo_un_aviso_discreto(st):
    from ui.views import hoy
    propio = repo.crear_plan(st.conn, "Global Master", st.perfil_id)
    st.plan_id = propio
    sin_curso = _textos(hoy.build(st, lambda: None, lambda: None))
    assert "Esta semana" in sin_curso and "Empieza aquí" not in sin_curso and "Owee" not in sin_curso
    curso.crear_plan_del_curso(st.conn, st.perfil_id)
    saltos = []
    cuerpo = hoy.build(st, lambda: None, lambda: None, ir_owee=lambda: saltos.append("owee"))
    texto = _textos(cuerpo)
    assert "Esta semana" in texto and "Aprende Owee · opcional" in texto and "Lección 0.1" in texto and "Empieza aquí" not in texto
    assert texto.index("Esta semana") < texto.index("Aprende Owee · opcional")      # lo tuyo va arriba, Owee al final
    _todos(cuerpo, ft.ListTile)[-1].on_click(None)
    assert saltos == ["owee"]


def test_si_eliges_el_curso_a_mano_hoy_muestra_el_curso_sin_el_aviso(st):
    from ui.views import hoy
    repo.crear_plan(st.conn, "Global Master", st.perfil_id)
    p = curso.crear_plan_del_curso(st.conn, st.perfil_id)
    st.plan_id = p
    assert "Aprende Owee · opcional" not in _textos(hoy.build(st, lambda: None, lambda: None))


def test_siguiente_leccion_avanza_y_termina(st):
    p = curso.crear_plan_del_curso(st.conn, st.perfil_id)
    assert curso.siguiente_leccion(st.conn, p)["id"] == "0.1"
    for l in curso.lecciones():
        curso.marcar_leccion(st.conn, p, l["id"], True)
    assert curso.siguiente_leccion(st.conn, p) is None
