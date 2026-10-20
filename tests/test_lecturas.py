"""Gestor de lecturas: BibTeX, estados, fichas, tarjetas y sincronización."""

import pytest

from database import db, repo
from engine import biblio
from engine.merge import fusionar

BIB = r"""
@comment{esto se ignora}
@string{rev = "Revista X"}
@article{garcia2020educacion,
  author = {Garc{\'\i}a, Mar{\'\i}a and L{\'o}pez-Y{\'a}\~nez, Jos{\'e} and Smith, John},
  title = {{Educaci{\'o}n} rural en {Bolivia}: un estudio de caso},
  journal = {Revista Latinoamericana de Educaci{\'o}n},
  year = {2020}, month = mar,
  doi = {10.1234/ABC.2020.01},
  url = "https://example.org/articulo"
}
@book(smith2018,
  author = "Smith, John",
  title = "Research Design",
  publisher = {Sage},
  year = 2018
)
@misc{sin_titulo, author = {Nadie}}
"""


@pytest.fixture
def conn():
    c = db.init_db(":memory:")
    repo.crear_plan(c, "Tesis", 1)
    return c


def test_leer_bibtex_con_acentos_llaves_y_formas_de_valor():
    r = biblio.leer_bibtex(BIB)
    assert [x["clave"] for x in r] == ["garcia2020educacion", "smith2018"]      # sin título: se omite
    a = r[0]
    assert a["titulo"] == "Educación rural en Bolivia: un estudio de caso"
    assert a["autores"] == "García, María; López-Yáñez, José; Smith, John"
    assert a["anio"] == 2020 and a["doi"] == "10.1234/ABC.2020.01" and a["fuente"].endswith("Educación")
    assert r[1]["tipo"] == "book" and r[1]["fuente"] == "Sage" and r[1]["anio"] == 2018


def test_ida_y_vuelta_bibtex():
    refs = biblio.leer_bibtex(BIB)
    filas = [{"titulo": r["titulo"], "autores": r["autores"], "anio": r["anio"], "fuente": r["fuente"], "doi": r["doi"],
              "url": r["url"], "tipo_bib": r["tipo"], "clave_bib": r["clave"]} for r in refs]
    otra = biblio.leer_bibtex(biblio.a_bibtex(filas))
    assert [(r["titulo"], r["autores"], r["anio"], r["doi"]) for r in otra] == [(r["titulo"], r["autores"], r["anio"], r["doi"]) for r in refs]


def test_claves_unicas_si_faltan():
    filas = [{"titulo": "Redes neuronales", "autores": "Pérez, Ana", "anio": 2021}] * 2
    claves = [x["clave"] for x in biblio.leer_bibtex(biblio.a_bibtex(filas))]
    assert len(set(claves)) == 2 and claves[0].startswith("perez2021")


def test_citar_y_fichas():
    l = {"titulo": "T", "autores": "A, x; B, y; C, z", "anio": 2020, "fuente": "Rev", "doi": "10/x", "pregunta": "¿Qué?",
         "metodo": "", "hallazgos": "Mucho", "notas": ""}
    assert biblio.citar(l) == "A et al. (2020). T"
    assert biblio.citar({"titulo": "T", "autores": "A, x; B, y", "anio": None}) == "A y B. T"
    md = biblio.fichas_markdown([l], {"pregunta": "Question"})
    assert "**Question:** ¿Qué?" in md and "**Hallazgos:** Mucho" in md and "Método" not in md


def test_importar_bibtex_no_duplica(conn):
    p = repo.planes(conn, 1)[0]["id"]
    assert repo.importar_bibtex(conn, p, BIB) == (2, 0)
    assert repo.importar_bibtex(conn, p, BIB) == (0, 2)
    assert len(repo.lecturas(conn, p)) == 2


def test_agregar_lectura_detecta_duplicados_por_doi_y_por_titulo(conn):
    p = repo.planes(conn, 1)[0]["id"]
    a = repo.agregar_lectura(conn, p, "Uno", doi="10.1/X")
    assert repo.agregar_lectura(conn, p, "Otro título", doi="10.1/x") == a
    b = repo.agregar_lectura(conn, p, "Dos", anio=2020)
    assert repo.agregar_lectura(conn, p, "dos", anio=2020) == b and repo.agregar_lectura(conn, p, "Dos", anio=2021) != b


def test_estados_fecha_y_resumen(conn):
    p = repo.planes(conn, 1)[0]["id"]
    a, _b = repo.agregar_lectura(conn, p, "A"), repo.agregar_lectura(conn, p, "B", prioridad=1)
    assert [x["titulo"] for x in repo.lecturas(conn, p)] == ["B", "A"]           # prioridad 1 primero
    repo.editar_lectura(conn, a, estado="leyendo")
    assert repo.lecturas(conn, p)[0]["titulo"] == "A"                            # «leyendo» va arriba
    repo.editar_lectura(conn, a, estado="leido")
    assert repo.lectura(conn, a)["fecha_leido"] is not None
    assert repo.resumen_lecturas(conn, p) == {"por_leer": 1, "leyendo": 0, "leido": 1, "semana": 1}
    repo.editar_lectura(conn, a, estado="por_leer")
    assert repo.lectura(conn, a)["fecha_leido"] is None
    with pytest.raises(ValueError):
        repo.editar_lectura(conn, a, estado="roto")


def test_filtros_y_etiquetas(conn):
    p = repo.planes(conn, 1)[0]["id"]
    repo.agregar_lectura(conn, p, "Teoría crítica", etiquetas="teoría, método", autores="Freire, Paulo")
    repo.agregar_lectura(conn, p, "Estudio de caso", etiquetas="caso")
    assert repo.todas_las_etiquetas(conn, p) == ["caso", "método", "teoría"]
    assert [x["titulo"] for x in repo.lecturas(conn, p, etiqueta="caso")] == ["Estudio de caso"]
    assert [x["titulo"] for x in repo.lecturas(conn, p, texto="freire")] == ["Teoría crítica"]
    assert repo.lecturas(conn, p, estado="leido") == []


def test_ficha_a_tarjetas(conn):
    p = repo.planes(conn, 1)[0]["id"]
    l = repo.agregar_lectura(conn, p, "Estudio", autores="Pérez, A", anio=2022, pregunta="¿Mejora la lectura?",
                             hallazgos="Sí, un 12 %")
    plantillas = {"pregunta": "{cita}: ¿cuál es la pregunta de investigación?", "hallazgos": "{cita}: ¿qué encontró?",
                  "metodo": "{cita}: ¿qué método usó?"}
    assert repo.tarjetas_de_lectura(conn, l, plantillas) == 2                    # el método está vacío: sin tarjeta
    assert repo.tarjetas_de_lectura(conn, l, plantillas) == 0                    # sin duplicar
    q = conn.execute("SELECT pregunta, respuesta, origen FROM tarjetas WHERE respuesta='Sí, un 12 %'").fetchone()
    assert q["pregunta"].startswith("Pérez (2022). Estudio: ") and q["origen"] == "lectura"


def test_borrar_plan_borra_sus_lecturas_y_borrar_material_solo_desvincula(conn):
    p = repo.planes(conn, 1)[0]["id"]
    m = repo.agregar_material(conn, p, "PDF", "pdf", "h1", "a.pdf", "/x/a.pdf", 10)
    l = repo.agregar_lectura(conn, p, "Con PDF", material_id=m)
    repo.borrar_material(conn, m)
    assert repo.lectura(conn, l)["material_id"] is None
    repo.borrar_plan(conn, p)
    assert conn.execute("SELECT COUNT(*) FROM lecturas").fetchone()[0] == 0


def test_las_lecturas_se_sincronizan_entre_equipos(tmp_path):
    a, b = db.init_db(str(tmp_path / "a.db")), db.init_db(str(tmp_path / "b.db"))
    pa = repo.crear_plan(a, "Tesis", 1)
    repo.agregar_lectura(a, pa, "Lectura de A", autores="X, y", hallazgos="v1")
    a.close()
    fusionar(b, str(tmp_path / "a.db"))
    assert b.execute("SELECT titulo, hallazgos FROM lecturas").fetchone()[:] == ("Lectura de A", "v1")
    b.execute("SELECT id FROM planes").fetchone()[0]
    repo.editar_lectura(b, b.execute("SELECT id FROM lecturas").fetchone()[0], hallazgos="v2", estado="leido")
    b.commit()
    b.close()
    a = db.init_db(str(tmp_path / "a.db"))
    fusionar(a, str(tmp_path / "b.db"))
    f = a.execute("SELECT hallazgos, estado, plan_id FROM lecturas").fetchone()
    assert f["hallazgos"] == "v2" and f["estado"] == "leido" and f["plan_id"] == pa


def test_actualizar_una_base_de_la_version_anterior_crea_la_tabla(tmp_path):
    ruta = str(tmp_path / "vieja.db")
    c = db.init_db(ruta)
    c.execute("DROP TABLE lecturas")
    c.execute("PRAGMA user_version=1")
    c.commit()
    c.close()
    c = db.init_db(ruta)
    assert c.execute("PRAGMA user_version").fetchone()[0] == db.VERSION_ESQUEMA
    assert c.execute("SELECT COUNT(*) FROM lecturas").fetchone()[0] == 0
    assert list((tmp_path / "respaldos").glob(f"vieja-antes-de-v{db.VERSION_ESQUEMA}-*.db"))
