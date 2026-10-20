"""Curso de Owee dentro de la app: datos, plan, tarjetas de glifos y vocabulario, y dibujo de las lecciones."""
import flet as ft
import pytest

import i18n
from database import db, repo
from i18n import owee
from owee_curso import bloques, curso
from owee_curso.datos import LEXICO, NIVELES
from ui.components.owee_texto import texto_tarjeta


@pytest.fixture
def conn():
    return db.init_db(":memory:")


def test_datos_del_curso():
    assert [n["n"] for n in NIVELES] == [0, 1, 2, 3]
    assert [len(n["lecciones"]) for n in NIVELES] == [5, 11, 12, 7]
    ids = [l["id"] for l in curso.lecciones()]
    assert len(ids) == len(set(ids)) == 35 and ids[0] == "0.1" and ids[-1] == "3.7"


def test_todo_el_vocabulario_de_las_lecciones_tiene_significado():
    """La app no inventa significados: cada palabra declarada está en el léxico de Owee."""
    for l in curso.lecciones():
        for w in bloques.palabras_de(l["md"]):
            assert w in LEXICO, f"{l['id']}: «{w}» no está en el léxico"
            assert all(owee.valida(p) for p in w.split("-")), f"{l['id']}: «{w}» no es Owee válido"


def test_el_analizador_reconoce_todos_los_tipos_de_bloque():
    tipos = {b["t"] for l in curso.lecciones() for b in bloques.parsear(l["md"])}
    assert {"md", "owee", "vocab", "tabla", "resp"} <= tipos


def test_bloque_owee_recibe_su_traduccion_y_los_numeros_quedan_marcados():
    bs = bloques.parsear("```owee\nsade go duma\n```\n\n*El sol sube.*\n\nSuma: [[2 + 3 = 5]]\n")
    assert bs[0] == {"t": "owee", "lineas": ["sade go duma"], "traduccion": "El sol sube."}
    assert bs[1] == {"t": "md", "texto": "Suma: `2 + 3 = 5`"}


def test_tabla_y_respuestas():
    bs = bloques.parsear("| Glifo | Romano |\n|---|---|\n| `a` | a |\n\n<!--resp-->\n**Ej.** `me nara`\n<!--/resp-->")
    assert bs[0]["cab"] == ["Glifo", "Romano"] and bs[0]["filas"] == [["`a`", "a"]]
    assert bs[1]["t"] == "resp" and "me nara" in bs[1]["md"]


def test_plan_del_curso_se_crea_una_sola_vez(conn):
    p = curso.crear_plan_del_curso(conn, 1)
    assert curso.crear_plan_del_curso(conn, 1) == p
    assert len(repo.unidades(conn, p)) == 4
    assert sum(len(repo.temas(conn, u["id"])) for u in repo.unidades(conn, p)) == 35
    assert [c["nombre"] for c in repo.carpetas(conn, 1)] == ["Owee"]
    assert curso.estado_leccion(conn, p, "0.1") == "pendiente"
    curso.marcar_leccion(conn, p, "0.1", True)
    assert curso.estado_leccion(conn, p, "0.1") == "completado"
    assert 0 < repo.progreso(conn, p) < 1


def test_tarjetas_de_glifos_y_vocabulario(conn):
    p = curso.crear_plan_del_curso(conn, 1)
    assert len(curso.tarjetas_de_leccion("0.1")) >= 4
    assert len([x for x in curso.tarjetas_de_leccion("0.2") if x[0].startswith(curso.MARCA_GLIFO)]) == 56
    assert len(curso.tarjetas_de_leccion("0.4")) >= 10
    n = curso.crear_tarjetas_leccion(conn, p, "1.1")
    assert n > 0 and curso.crear_tarjetas_leccion(conn, p, "1.1") == 0      # sin duplicar
    filas = conn.execute("SELECT pregunta, respuesta, origen FROM tarjetas").fetchall()
    assert {f["origen"] for f in filas} == {"owee", "produccion"}
    # solo texto latino con marca: los glifos (área privada) nunca se guardan
    assert not any(owee.tiene_glifos(f["pregunta"] + f["respuesta"]) for f in filas)
    assert any(f["pregunta"].startswith(curso.MARCA_OWEE) for f in filas)
    assert any(f["respuesta"].startswith(curso.MARCA_OWEE) for f in filas)    # y la tarjeta inversa


def test_las_tarjetas_van_al_tema_de_su_leccion(conn):
    p = curso.crear_plan_del_curso(conn, 1)
    curso.crear_tarjetas_leccion(conn, p, "0.2")
    r = conn.execute("""SELECT t.titulo, COUNT(*) n FROM tarjetas k JOIN temas t ON t.id=k.tema_id GROUP BY t.id""").fetchall()
    assert len(r) == 1 and r[0]["titulo"].startswith("0.2 ") and r[0]["n"] == 56


def test_texto_de_tarjeta_con_marcas():
    normal = texto_tarjeta("agua")
    assert isinstance(normal, ft.Text) and normal.value == "agua"
    solo = texto_tarjeta("[glifo]ka")
    assert owee.tiene_glifos(solo.controls[0].value) and len(solo.controls) == 1
    con = texto_tarjeta("[owee]suna")
    assert len(con.controls) == 2 and con.controls[1].value == "suna"
    assert texto_tarjeta("x", visible=False).visible is False


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width = [], ft.PagePlatform.LINUX, 1000

    def update(self, *a): pass
    def open(self, *a): pass
    def close(self, *a): pass
    def launch_url(self, *a): pass


@pytest.mark.parametrize("codigo", ["es", "en", "ja", "qow"])
def test_las_35_lecciones_se_dibujan_en_cualquier_idioma(conn, codigo):
    from ui.state import AppState
    from ui.views import aprende_owee
    st = AppState(_Pagina())
    st.conn = conn
    i18n.fijar_idioma(codigo)
    try:
        cuerpo = aprende_owee.build(st, lambda: None)
        assert cuerpo.controls                      # índice
        # cada lección: se abre el índice y se entra por su ListTile
        for l in curso.lecciones():
            st_ = aprende_owee.build(st, lambda: None)
            niveles = [c for c in st_.controls if isinstance(c, ft.ExpansionTile)]
            tile = next(x for n in niveles for x in n.controls if isinstance(x, ft.ListTile) and l["titulo"] in x.title.value)
            tile.on_click(None)
            assert len(st_.controls) > 3, l["id"]
    finally:
        i18n.fijar_idioma("es")
