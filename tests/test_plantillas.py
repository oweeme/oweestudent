"""Asistente de objetivo: plantillas por tipo, viabilidad del tiempo, creación del plan y pantalla."""
from datetime import date, timedelta
from types import SimpleNamespace

import flet as ft
import pytest

import i18n
from database import db, repo
from engine import plantillas as pl
from parsers.plan_parser import parse_plan

CASOS = {
    "asignatura": pl.Datos("asignatura", "Cálculo I", 8, 4, temario=[f"Tema {i}" for i in range(1, 15)]),
    "idioma": pl.Datos("idioma", "Alemán", 5, 12, nivel_actual="A1", nivel_meta="B1"),
    "tecnologia": pl.Datos("tecnologia", "Python", 6, 6, nivel_actual="principiante", proyecto="un bot de notas"),
    "posgrado": pl.Datos("posgrado", "Educación rural en Bolivia", 10, 12, etapa="inicio", lecturas_semana=4),
}


@pytest.fixture(autouse=True)
def _espanol():
    i18n.fijar_idioma("es")
    yield
    i18n.fijar_idioma("es")


@pytest.fixture
def conn():
    return db.init_db(":memory:")


@pytest.mark.parametrize("tipo", pl.TIPOS)
def test_cada_plantilla_genera_un_plan_que_la_app_entiende(tipo):
    d = CASOS[tipo]
    md = pl.generar_markdown(d)
    p = parse_plan(md)
    assert p["titulo"] and len(p["unidades"]) >= 2
    assert all(u["temas"] for u in p["unidades"])
    assert all("*" not in x and x.strip() for u in p["unidades"] for x in u["temas"])
    anterior = 0
    for u in p["unidades"]:
        assert 1 <= u["mes_ini"] <= u["mes_fin"] <= d.meses
        assert u["mes_ini"] >= anterior          # los módulos avanzan en el tiempo, sin ir hacia atrás
        anterior = u["mes_ini"]
    assert p["unidades"][-1]["mes_fin"] == d.meses          # el plan ocupa todo el tiempo disponible
    assert len(p["cronograma"]) >= 1 and {f["dia"] for f in p["cronograma"]} <= set(pl.DIAS)


def test_las_horas_por_semana_se_reflejan_en_el_cronograma():
    n = lambda h: sum(len([b for b in f["bloques"].values() if b not in ("", "—")]) for f in
                      parse_plan(pl.generar_markdown(pl.Datos("tecnologia", "Python", h, 4, "principiante")))["cronograma"])
    assert n(3) == 3 and n(6) == 6 and n(12) == 12


def test_validacion():
    assert pl.validar(pl.Datos("asignatura", "", 5, 3, temario=["a", "b"]))                       # sin objetivo
    assert pl.validar(pl.Datos("asignatura", "X", 5, 3, temario=["solo uno"]))                    # temario corto
    assert pl.validar(pl.Datos("idioma", "Ruso", 5, 6, "B1", "A2"))                               # meta menor que el nivel
    assert pl.validar(pl.Datos("idioma", "Ruso", 5, 6, "", "B1"))                                 # sin nivel
    assert pl.validar(pl.Datos("tecnologia", "Go", 0, 6)) and pl.validar(pl.Datos("tecnologia", "Go", 5, 0))
    assert pl.validar(pl.Datos("otro", "x")) and pl.validar(CASOS["idioma"]) == []
    with pytest.raises(ValueError):
        pl.generar_markdown(pl.Datos("asignatura", "", 5, 3))


def test_viabilidad_de_un_idioma():
    ok = pl.viabilidad(pl.Datos("idioma", "Alemán", 5, 12, "A1", "B1"))
    assert ok["necesarias"] == 260 and ok["ok"] and 250 < ok["disponibles"] < 270
    mal = pl.viabilidad(pl.Datos("idioma", "Alemán", 1, 6, "A0", "B2"))
    assert not mal["ok"] and mal["h_semana_necesarias"] > 15 and mal["meses_necesarios"] > 6
    assert "semana" in pl.mensaje_viabilidad(pl.Datos("idioma", "Alemán", 1, 6, "A0", "B2"))
    assert "alcanza" in pl.mensaje_viabilidad(CASOS["idioma"])


def test_viabilidad_de_las_demas_se_basa_en_los_temas():
    d = CASOS["asignatura"]
    v = pl.viabilidad(d)
    assert v["necesarias"] == len(pl._temas_de(pl._estructura(d))) * pl.HORAS_POR_TEMA > 0


def test_reparto_de_meses():
    assert pl._reparto([90, 170], 12) == [(1, 4), (5, 12)]
    assert pl._reparto([5], 1) == [(1, 1)]
    r = pl._reparto([1, 1, 1, 1, 1], 3)               # más módulos que meses: comparten mes
    assert r[0][0] == 1 and r[-1][1] == 3 and all(1 <= a <= b <= 3 for a, b in r)


def test_idioma_con_varios_niveles_tiene_un_modulo_por_nivel():
    p = parse_plan(pl.generar_markdown(pl.Datos("idioma", "Chino", 8, 24, "A0", "B2")))
    assert [u["titulo"].split()[-1] for u in p["unidades"]] == ["A1", "A2", "B1", "B2"]


def test_posgrado_salta_a_la_etapa_en_la_que_estas():
    n = lambda e: len(parse_plan(pl.generar_markdown(pl.Datos("posgrado", "Tema", 8, 10, etapa=e)))["unidades"])
    assert n("inicio") == 5 and n("revision") == 4 and n("escritura") == 2


def test_tecnologia_avanzada_no_repite_los_fundamentos():
    tit = lambda nv: [u["titulo"] for u in parse_plan(pl.generar_markdown(
        pl.Datos("tecnologia", "Rust", 6, 6, nv)))["unidades"]]
    assert any("Fundamentos" in x for x in tit("principiante")) and not any("Fundamentos" in x for x in tit("avanzado"))


@pytest.mark.parametrize("codigo", ["en", "de", "ru", "zh", "ja", "qow"])
def test_el_plan_se_genera_en_cualquier_idioma_con_la_misma_estructura(codigo):
    base = {k: pl.resumen(pl.generar_markdown(d)) for k, d in CASOS.items()}
    i18n.fijar_idioma(codigo)
    for k, d in CASOS.items():
        r = pl.resumen(pl.generar_markdown(d))
        assert r["temas"] == base[k]["temas"] and len(r["unidades"]) == len(base[k]["unidades"]), (codigo, k)
        assert [(a, b) for _, _, a, b in r["unidades"]] == [(a, b) for _, _, a, b in base[k]["unidades"]]


def test_en_ingles_el_texto_sale_en_ingles():
    i18n.fijar_idioma("en")
    md = pl.generar_markdown(CASOS["idioma"])
    assert "Listening" in md and "Escucha" not in md and "Lunes" in md      # estructura y días: siempre en español


def test_crear_plan_lo_guarda_con_fechas_meta_y_cronograma(conn):
    inicio = date(2026, 1, 12)
    pid = pl.crear_plan(conn, CASOS["idioma"], 1, inicio)
    assert repo.meta_semanal(conn, pid) == 5
    fechas = [r[0] for r in conn.execute("""SELECT t.fecha_programada FROM temas t JOIN unidades u ON u.id=t.unidad_id
                                           WHERE u.plan_id=?""", (pid,))]
    assert len(fechas) == 16 and all(f is not None for f in fechas)
    assert inicio.isoformat() <= min(fechas) and max(fechas) <= (inicio + timedelta(days=366)).isoformat()
    filas = conn.execute("SELECT dia, actividad FROM cronograma WHERE plan_id=?", (pid,)).fetchall()
    assert len(filas) == 5 and all(f["actividad"] not in ("", "—") for f in filas)
    assert conn.execute("SELECT titulo FROM planes WHERE id=?", (pid,)).fetchone()[0] == "Alemán: de A1 a B1"


def test_celdas_vacias_del_cronograma_no_se_guardan(conn):
    pid = pl.crear_plan(conn, pl.Datos("tecnologia", "Python", 8, 3, "principiante"), 1, date(2026, 1, 5))
    assert conn.execute("SELECT COUNT(*) FROM cronograma WHERE plan_id=? AND actividad IN ('','—')", (pid,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM cronograma WHERE plan_id=?", (pid,)).fetchone()[0] == 8


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.abiertos = [], ft.PagePlatform.LINUX, 1000, []

    def update(self, *a): pass
    def open(self, x): self.abiertos.append(x)
    def close(self, *a): pass


@pytest.mark.parametrize("codigo", ["es", "en", "ja"])
@pytest.mark.parametrize("tipo", pl.TIPOS)
def test_la_pantalla_del_asistente_crea_el_plan(conn, codigo, tipo):
    from ui.state import AppState
    from ui.views import asistente
    st = AppState(_Pagina())
    st.conn = conn
    i18n.fijar_idioma(codigo)
    llamadas = []
    cuerpo = asistente.build(st, lambda: llamadas.append("plan"), lambda: None)
    grupo = next(c for c in cuerpo.controls if isinstance(c, ft.RadioGroup))
    grupo.on_change(SimpleNamespace(control=SimpleNamespace(value=tipo)))
    zona_campos = cuerpo.controls[4]
    campos = zona_campos.controls
    d = CASOS[tipo]
    objetivo = campos[0]
    objetivo.value = d.objetivo
    aplanado = []
    for c in campos:
        aplanado += c.controls if isinstance(c, ft.Row) else [c]
    for c in aplanado:
        c.label if hasattr(c, "label") else None
        if tipo == "asignatura" and isinstance(c, ft.TextField) and c.multiline:
            c.value = "\n".join(d.temario)
    zona_campos.controls[-1].on_click(None)                       # Ver vista previa
    previa = cuerpo.controls[6]
    assert previa.controls, "debe mostrar la vista previa"
    tarjeta_previa = previa.controls[0]
    botones = [x for x in tarjeta_previa.content.content.controls if isinstance(x, ft.Row)][-1].controls
    botones[0].on_click(None)                                      # Crear plan
    assert llamadas == ["plan"] and st.plan_id
    assert repo.progreso(conn, st.plan_id) == 0
