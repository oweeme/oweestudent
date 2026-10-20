"""Exportar a Anki: CSV, paquete .apkg y (si está instalada la biblioteca oficial) importación real."""
import io
import json
import sqlite3
import zipfile
from datetime import date

import pytest

from database import db, repo
from engine import anki
from owee_curso import curso


class _Con:
    """Conexión con atajos a la asignatura y el tema de prueba (sqlite3.Connection no admite atributos nuevos)."""

    def __init__(self, c, plan, tema):
        self._c, self.plan, self.tema = c, plan, tema

    def __getattr__(self, nombre):
        return getattr(self._c, nombre)



@pytest.fixture
def conn():
    c = db.init_db(":memory:")
    plan = repo.crear_plan(c, "Redes: básico", 1)
    tema = repo.tema_para_tarjetas(c, plan, "Capa de transporte")
    repo.crear_tarjetas(c, tema, [("¿Qué es <TCP>?", "Protocolo\ncon conexión"), ("¿Qué es UDP?", "Sin conexión & rápido")], "manual")
    return _Con(c, plan, tema)


def test_html_escapa_y_convierte_glifos():
    assert anki.a_html("a < b & c\nd") == "a &lt; b &amp; c<br>d"
    g = anki.a_html("[glifo]ka")
    assert 'class="owee"' in g and "<small>" not in g
    w = anki.a_html("[owee]suna")
    assert 'class="owee"' in w and "<small>suna</small>" in w
    assert anki.a_texto("[glifo]ka") == "ka" and anki.a_texto("normal") == "normal"


def test_csv_con_etiquetas_y_sin_glifos(conn):
    p = curso.crear_plan_del_curso(conn, 1)
    curso.crear_tarjetas_leccion(conn, p, "0.1")
    texto = anki.a_csv(anki.tarjetas_a_exportar(conn, 1, conn.plan))
    import csv
    filas = list(csv.reader(io.StringIO(texto), delimiter="\t"))
    assert filas[0] == ["¿Qué es <TCP>?", "Protocolo\ncon conexión", "Redes:_básico Capa_de_transporte"]
    todo = anki.a_csv(anki.tarjetas_a_exportar(conn, 1))
    assert "" not in todo and "[glifo]" not in todo


def test_alcance_de_la_exportacion(conn):
    otro = repo.tema_para_tarjetas(conn, repo.crear_plan(conn, "Otra", 1), "T")
    repo.crear_tarjetas(conn, otro, [("x?", "x")], "manual")
    assert len(anki.tarjetas_a_exportar(conn, 1)) == 3 and len(anki.tarjetas_a_exportar(conn, 1, conn.plan)) == 2
    assert len(anki.tarjetas_a_exportar(conn, 1, tema_id=otro)) == 1


def test_estructura_del_paquete(conn, tmp_path):
    ruta = tmp_path / "x.apkg"
    info = anki.crear_apkg(anki.tarjetas_a_exportar(conn, 1), ruta)
    assert info == {"tarjetas": 2, "mazos": 1, "con_fuente": False}
    with zipfile.ZipFile(ruta) as z:
        assert set(z.namelist()) == {"collection.anki2", "media"} and json.loads(z.read("media")) == {}
        bd = tmp_path / "c.db"
        bd.write_bytes(z.read("collection.anki2"))
    c = sqlite3.connect(bd)
    assert c.execute("SELECT COUNT(*) FROM notes").fetchone()[0] == 2 == c.execute("SELECT COUNT(*) FROM cards").fetchone()[0]
    assert c.execute("SELECT ver FROM col").fetchone()[0] == 11
    nombres = [d["name"] for d in json.loads(c.execute("SELECT decks FROM col").fetchone()[0]).values()]
    assert "OweeStudent::Redes: básico" in nombres


def test_guid_estable_para_que_reimportar_no_duplique(conn, tmp_path):
    def guids():
        anki.crear_apkg(anki.tarjetas_a_exportar(conn, 1), tmp_path / "y.apkg")
        with zipfile.ZipFile(tmp_path / "y.apkg") as z:
            (tmp_path / "y.db").write_bytes(z.read("collection.anki2"))
        return sorted(r[0] for r in sqlite3.connect(tmp_path / "y.db").execute("SELECT guid FROM notes"))
    assert guids() == guids() and len(set(guids())) == 2


def test_la_fuente_owee_viaja_solo_si_hace_falta(conn, tmp_path):
    p = curso.crear_plan_del_curso(conn, 1)
    curso.crear_tarjetas_leccion(conn, p, "0.1")
    info = anki.crear_apkg(anki.tarjetas_a_exportar(conn, 1), tmp_path / "o.apkg")
    assert info["con_fuente"] and info["mazos"] == 2
    with zipfile.ZipFile(tmp_path / "o.apkg") as z:
        assert json.loads(z.read("media")) == {"0": "_OweeSans.ttf"} and len(z.read("0")) > 10_000


def test_el_progreso_de_repaso_se_traduce_a_una_tarjeta_de_repaso_de_anki(conn, tmp_path):
    k = conn.execute("SELECT id FROM tarjetas WHERE pregunta LIKE '%UDP%'").fetchone()[0]
    repo.repasar_tarjeta(conn, k, 4)
    repo.repasar_tarjeta(conn, k, 4)
    anki.crear_apkg(anki.tarjetas_a_exportar(conn, 1), tmp_path / "p.apkg", con_progreso=True)
    with zipfile.ZipFile(tmp_path / "p.apkg") as z:
        (tmp_path / "p.db").write_bytes(z.read("collection.anki2"))
    c = sqlite3.connect(tmp_path / "p.db")
    tipos = sorted(r[0] for r in c.execute("SELECT type FROM cards"))
    assert tipos == [0, 2]
    anki.crear_apkg(anki.tarjetas_a_exportar(conn, 1), tmp_path / "q.apkg", con_progreso=False)
    with zipfile.ZipFile(tmp_path / "q.apkg") as z:
        (tmp_path / "q.db").write_bytes(z.read("collection.anki2"))
    assert {r[0] for r in sqlite3.connect(tmp_path / "q.db").execute("SELECT type FROM cards")} == {0}


def test_importacion_real_con_la_biblioteca_oficial_de_anki(conn, tmp_path):
    pytest.importorskip("anki")
    from anki.collection import Collection, ImportAnkiPackageOptions, ImportAnkiPackageRequest
    p = curso.crear_plan_del_curso(conn, 1)
    curso.crear_tarjetas_leccion(conn, p, "0.1")
    k = conn.execute("SELECT id FROM tarjetas WHERE pregunta LIKE '%TCP%'").fetchone()[0]
    repo.repasar_tarjeta(conn, k, 4)
    repo.repasar_tarjeta(conn, k, 4)
    prox = conn.execute("SELECT proximo_repaso FROM tarjetas WHERE id=?", (k,)).fetchone()[0]
    paquete = tmp_path / "t.apkg"
    anki.crear_apkg(anki.tarjetas_a_exportar(conn, 1), paquete)
    col = Collection(str(tmp_path / "destino.anki2"))
    try:
        peticion = ImportAnkiPackageRequest(package_path=str(paquete), options=ImportAnkiPackageOptions(with_scheduling=True))
        col.import_anki_package(peticion)
        assert col.note_count() == col.card_count() == 6
        carta = col.get_card(col.find_cards("TCP")[0])
        assert carta.type == 2 and (carta.due - col.sched.today) == (date.fromisoformat(prox) - date.today()).days
        assert "<TCP>" in carta.note().fields[0].replace("&lt;", "<").replace("&gt;", ">")
        assert "_OweeSans.ttf" in __import__("os").listdir(col.media.dir())
        col.import_anki_package(peticion)                       # otra vez: no duplica
        assert col.note_count() == 6
    finally:
        col.close()
