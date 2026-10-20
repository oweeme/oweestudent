"""Escritor de monografías, tesis y libros: esqueletos, citas, referencias, exportación y revisión."""
import zipfile
from datetime import date, timedelta

import pytest
from conftest import Con

import i18n
from database import db, repo
from engine import busqueda as bq
from engine import escritura as es
from engine import material as mat
from engine.merge import fusionar


@pytest.fixture(autouse=True)
def _espanol():
    i18n.fijar_idioma("es")
    yield
    i18n.fijar_idioma("es")


@pytest.fixture
def conn():
    c = db.init_db(":memory:")
    plan = repo.crear_plan(c, "Tesis", 1)
    repo.importar_bibtex(c, plan, """
@article{ruiz2021transporte, author = {Ruiz, Ana and Quispe, Luis}, title = {Transporte escolar y deserción}, year = {2021},
  journal = {Revista de Educación}, doi = {10.1/abc}}
@book{freire1970, author = {Freire, Paulo}, title = {Pedagogía del oprimido}, year = {1970}, publisher = {Siglo XXI}}
@article{mamani2019, author = {Mamani, A. and Choque, B. and Torrez, C.}, title = {Escuelas rurales}, year = {2019}, journal = {Rev. Andina}}
""")
    return Con(c, plan=plan)


def test_esqueletos_por_tipo_y_metas():
    for tipo, n in (("monografia", 5), ("ensayo", 6), ("tesis", 7)):
        sk = es.esqueleto(tipo)
        assert len(sk) == n and 98 <= sum(p for _, p, _ in sk) <= 102, tipo
    libro = es.esqueleto("libro", 4)
    assert [x[0] for x in libro] == ["Prólogo", "Capítulo 1", "Capítulo 2", "Capítulo 3", "Capítulo 4", "Epílogo"]
    with pytest.raises(ValueError):
        es.esqueleto("poema")


def test_crear_escrito_reparte_la_meta(conn):
    e = es.crear_escrito(conn, conn.plan, "La educación rural", "monografia", 3000, date.today() + timedelta(days=30), "Ana", "apa")
    s = es.secciones(conn, e)
    assert [x["titulo"] for x in s][:2] == ["Introducción", "Antecedentes"] and s[0]["notas"]
    assert abs(sum(x["meta_palabras"] for x in s) - 3000) <= 50 and s[2]["meta_palabras"] == 1200      # el desarrollo pesa 40 %
    assert es.crear_escrito(conn, conn.plan, "T", "tesis") and es.escrito(conn, e)["meta_palabras"] == 3000
    with pytest.raises(ValueError):
        es.crear_escrito(conn, conn.plan, "x", "novela")
    with pytest.raises(ValueError):
        es.crear_escrito(conn, conn.plan, "x", "ensayo", estilo="chicago")


def test_secciones_se_editan_se_mueven_y_se_borran(conn):
    e = es.crear_escrito(conn, conn.plan, "Ensayo", "ensayo")
    ids = [s["id"] for s in es.secciones(conn, e)]
    es.mover_seccion(conn, ids[0], 1)
    assert [s["id"] for s in es.secciones(conn, e)][:2] == [ids[1], ids[0]]
    es.mover_seccion(conn, ids[1], -1)                        # ya es la primera: no pasa nada
    assert [s["id"] for s in es.secciones(conn, e)][:2] == [ids[1], ids[0]]
    es.editar_seccion(conn, ids[0], texto="Hola mundo", titulo="Mi intro", meta_palabras=200)
    s = es.seccion(conn, ids[0])
    assert (s["texto"], s["titulo"], s["meta_palabras"]) == ("Hola mundo", "Mi intro", 200)
    nueva = es.agregar_seccion(conn, e, "Anexo")
    assert es.secciones(conn, e)[-1]["id"] == nueva
    es.borrar_seccion(conn, nueva)
    assert len(es.secciones(conn, e)) == 6
    es.borrar_escrito(conn, e)
    assert conn.execute("SELECT COUNT(*) FROM secciones").fetchone()[0] == 0


def test_contar_palabras_ignora_citas_y_cuenta_cjk():
    assert es.contar_palabras("Hola mundo [@ruiz2021transporte] y adiós [@a; @b, p. 3].") == 4
    assert es.contar_palabras("") == 0 and es.contar_palabras("well-known don't") == 2
    assert es.contar_palabras("机器学习很有趣") == 7 and es.contar_palabras("Python 机器 学习") == 5


def test_progreso_y_ritmo_necesario(conn):
    e = es.crear_escrito(conn, conn.plan, "M", "monografia", 1000, date.today() + timedelta(days=10))
    es.editar_seccion(conn, es.secciones(conn, e)[0]["id"], texto="palabra " * 200)
    p = es.progreso(conn, e)
    assert p["palabras"] == 200 and p["meta"] == 1000 and p["porcentaje"] == 20 and p["dias"] == 10
    assert p["palabras_por_dia"] == 80 and p["secciones"][0]["palabras"] == 200
    es.editar_escrito(conn, e, fecha_limite=date.today() - timedelta(days=1))
    assert es.progreso(conn, e)["palabras_por_dia"] is None


def test_claves_unicas_y_estables(conn):
    k = es.claves_del_plan(conn, conn.plan)
    assert set(k) == {"ruiz2021transporte", "freire1970", "mamani2019"}
    repo.agregar_lectura(conn, conn.plan, "Sin clave", autores="Pérez, Juan", anio=2022)
    repo.agregar_lectura(conn, conn.plan, "Sin clave dos", autores="Pérez, Juan", anio=2022)
    k2 = es.claves_del_plan(conn, conn.plan)
    assert len(k2) == 5 and "perez2022sinclave" in k2 and "perez2022sinclave2" not in k2 or len(set(k2)) == 5
    assert es.claves_del_plan(conn, conn.plan).keys() == k2.keys()


def test_citas_en_el_texto():
    t = "Dato [@a]. Otro [@b, p. 12]. Varios [@c; @d, pp. 3-4]. Nada [esto no]."
    assert es.citas_en(t) == [("a", None), ("b", "12"), ("c", None), ("d", "3-4")]


def test_cita_corta_segun_el_numero_de_autores(conn):
    k = es.claves_del_plan(conn, conn.plan)
    assert es.cita_corta(k["freire1970"]) == "Freire, 1970"
    assert es.cita_corta(k["ruiz2021transporte"], "4") == "Ruiz y Quispe, 2021, p. 4"
    assert es.cita_corta(k["mamani2019"]) == "Mamani et al., 2019"
    i18n.fijar_idioma("en")
    assert es.cita_corta(k["ruiz2021transporte"]) == "Ruiz & Quispe, 2021"


def test_referencias_apa(conn):
    k = es.claves_del_plan(conn, conn.plan)
    assert es.referencia(k["ruiz2021transporte"]) == "Ruiz, A. y Quispe, L. (2021). Transporte escolar y deserción. *Revista de Educación*. https://doi.org/10.1/abc"
    assert es.referencia(k["freire1970"]).startswith("Freire, P. (1970). Pedagogía del oprimido.")
    assert es.referencia(k["ruiz2021transporte"], "numerico", 3).startswith("[3] Ruiz, A. y Quispe, L.")
    i18n.fijar_idioma("en")
    assert es.referencia(k["ruiz2021transporte"]).startswith("Ruiz, A., & Quispe, L. (2021).")


def test_compilar_convierte_citas_y_arma_las_referencias(conn):
    e = es.crear_escrito(conn, conn.plan, "La educación rural", "ensayo", autor="Ana")
    a, b = [s["id"] for s in es.secciones(conn, e)][:2]
    es.editar_seccion(conn, a, texto="El transporte reduce la deserción [@ruiz2021transporte, p. 14].\n\nFreire lo anticipó [@freire1970; @mamani2019].")
    es.editar_seccion(conn, b, texto="Otra vez [@ruiz2021transporte] y una cita rota [@inventada].")
    d = es.compilar(conn, e)
    assert d["bloques"][0]["parrafos"][0] == "El transporte reduce la deserción (Ruiz y Quispe, 2021, p. 14)."
    assert d["bloques"][0]["parrafos"][1] == "Freire lo anticipó (Freire, 1970; Mamani et al., 2019)."
    assert "(Ruiz y Quispe, 2021)" in d["bloques"][1]["parrafos"][0] and "(inventada?)" in d["bloques"][1]["parrafos"][0]
    assert d["sin_fuente"] == ["inventada"] and len(d["referencias"]) == 3
    assert d["referencias"][0].startswith("Freire")                         # APA: orden alfabético
    assert d["palabras"] == es.contar_palabras(es.seccion(conn, a)["texto"]) + es.contar_palabras(es.seccion(conn, b)["texto"])


def test_estilo_numerico_numera_por_orden_de_aparicion(conn):
    e = es.crear_escrito(conn, conn.plan, "T", "ensayo", estilo="numerico")
    a = es.secciones(conn, e)[0]["id"]
    es.editar_seccion(conn, a, texto="Primero Freire [@freire1970]. Luego Ruiz [@ruiz2021transporte, p. 2]. Y otra vez Freire [@freire1970].")
    d = es.compilar(conn, e)
    assert d["bloques"][0]["parrafos"][0] == "Primero Freire [1]. Luego Ruiz [2, p. 2]. Y otra vez Freire [1]."
    assert [r[:3] for r in d["referencias"]] == ["[1]", "[2]"] and "Freire" in d["referencias"][0]


def test_exportar_markdown_y_html(conn):
    e = es.crear_escrito(conn, conn.plan, "Educación <rural> & más", "ensayo", autor="Ana")
    es.editar_seccion(conn, es.secciones(conn, e)[0]["id"], texto="Texto con **negrita**, *cursiva* y <b>etiqueta</b> [@freire1970].")
    d = es.compilar(conn, e)
    md = es.a_markdown(d)
    assert md.startswith("# Educación <rural> & más\n\n*Ana*") and "## Introducción y tesis" in md and "(Freire, 1970)" in md and "## Referencias" in md
    h = es.a_html(d)
    assert "<h1>Educación &lt;rural&gt; &amp; más</h1>" in h and "<strong>negrita</strong>" in h and "<em>cursiva</em>" in h
    assert "&lt;b&gt;etiqueta" in h and "<script" not in h and '<p class="ref">' in h


def test_exportar_word(conn, tmp_path):
    docx = pytest.importorskip("docx")
    e = es.crear_escrito(conn, conn.plan, "Mi tesis", "tesis", autor="Ana")
    es.editar_seccion(conn, es.secciones(conn, e)[1]["id"], texto="Dato **importante** [@ruiz2021transporte].")
    ruta = tmp_path / "t.docx"
    es.a_docx(es.compilar(conn, e), ruta)
    assert zipfile.is_zipfile(ruta)
    textos = [p.text for p in docx.Document(str(ruta)).paragraphs]
    assert "Mi tesis" in textos and "Introducción" in textos and "Dato importante (Ruiz y Quispe, 2021)." in textos
    assert any(x.startswith("Ruiz, A. y Quispe, L. (2021)") for x in textos) and es.docx_disponible()


def test_revision_local_de_la_redaccion():
    assert es.revisar_seccion("") == ["La sección está vacía."]
    largo = " ".join(["palabra"] * 45) + "."
    avisos = es.revisar_seccion(largo, claves={"a"})
    assert any("frase de más de 40 palabras" in a for a in avisos)
    sin_cita = " ".join(f"idea{i}" for i in range(130)) + "."
    assert any("no cita ninguna fuente" in a for a in es.revisar_seccion(sin_cita))
    assert not any("no cita" in a for a in es.revisar_seccion(sin_cita + " [@a]", claves={"a"}))
    assert any("Citas sin lectura registrada: x" in a for a in es.revisar_seccion("Algo [@x].", claves={"a"}))
    assert any("Repites mucho «educación»" in a for a in es.revisar_seccion("La educación es clave. " * 8 + "Y la educación cambia.", 0))
    assert any("Llevas" in a for a in es.revisar_seccion("Texto corto de prueba aquí.", meta=500))
    assert any("Pasas de la meta" in a for a in es.revisar_seccion("palabra otra " * 40, meta=20))
    assert es.revisar_seccion("Una frase breve y limpia. Otra frase. Y una tercera con cierre.")[0].startswith("Se ve ordenada")


def _indice_con_libro(conn, tmp_path):
    f = tmp_path / "libro.md"
    f.write_text("El transporte escolar reduce la deserción en un doce por ciento en comunidades rurales del altiplano boliviano.\n" * 3, encoding="utf-8")
    h = mat.hash_archivo(str(f))
    mid = repo.agregar_material(conn, conn.plan, "Informe de campo", "md", h, "libro.md", str(f), 10)
    idx = bq.Indice(tmp_path / "indice.db")
    idx.indexar_material(h, str(f))
    return idx, mid


def test_fuentes_sugeridas_indican_si_se_pueden_citar(conn, tmp_path):
    idx, mid = _indice_con_libro(conn, tmp_path)
    r = es.fuentes_para(conn, idx, conn.plan, "transporte escolar deserción")
    assert r and all(x["clave"] is None for x in r if x["fuente"].origen == "material")       # el archivo aún no es una lectura
    lid = conn.execute("SELECT id FROM lecturas WHERE clave_bib='ruiz2021transporte'").fetchone()[0]
    repo.editar_lectura(conn, lid, material_id=mid, hallazgos="El transporte escolar reduce la deserción")
    r = es.fuentes_para(conn, idx, conn.plan, "transporte escolar deserción")
    assert {x["clave"] for x in r} == {"ruiz2021transporte"}               # el archivo y la ficha apuntan a la misma lectura


def test_borrador_con_ia_solo_cita_lecturas_registradas(conn, tmp_path):
    idx, mid = _indice_con_libro(conn, tmp_path)
    lid = conn.execute("SELECT id FROM lecturas WHERE clave_bib='ruiz2021transporte'").fetchone()[0]
    repo.editar_lectura(conn, lid, hallazgos="El transporte escolar reduce la deserción")
    vistos = []

    def falso(prompt, sistema, tokens):
        vistos.append(prompt)
        return "El transporte reduce la deserción [1]. Un dato del informe [2]. Y otro inventado [9]."
    r = es.borrador_ia(conn, idx, conn.plan, "Resultados", "transporte escolar deserción", llm=falso)
    assert "FRAGMENTOS" in vistos[0] and "SOLO" in vistos[0]
    assert "[@ruiz2021transporte]" in r["texto"] and "[9]" not in r["texto"]
    assert r["sin_registrar"] == ["Informe de campo · p. 1"]
    sin = es.borrador_ia(conn, idx, conn.plan, "Criptomonedas", "blockchain", llm=falso)
    assert sin["sin_fuentes"] and sin["texto"] == ""
    no = es.borrador_ia(conn, idx, conn.plan, "Resultados", "transporte escolar", llm=lambda *a: "NO_ENCONTRADO")
    assert no["no_alcanza"] and no["texto"] == ""


def test_los_escritos_se_sincronizan(tmp_path):
    a, b = db.init_db(str(tmp_path / "a.db")), db.init_db(str(tmp_path / "b.db"))
    p = repo.crear_plan(a, "Tesis", 1)
    e = es.crear_escrito(a, p, "Mi tesis", "tesis")
    es.editar_seccion(a, es.secciones(a, e)[0]["id"], texto="Resumen escrito en A")
    a.close()
    fusionar(b, str(tmp_path / "a.db"))
    assert b.execute("SELECT COUNT(*) FROM secciones").fetchone()[0] == 7
    sid = b.execute("SELECT id FROM secciones WHERE texto LIKE 'Resumen%'").fetchone()[0]
    es.editar_seccion(b, sid, texto="Resumen corregido en B")
    b.close()
    a = db.init_db(str(tmp_path / "a.db"))
    fusionar(a, str(tmp_path / "b.db"))
    assert a.execute("SELECT texto FROM secciones WHERE id=?", (es.secciones(a, e)[0]["id"],)).fetchone()[0] == "Resumen corregido en B"


def test_el_texto_del_escrito_es_buscable_en_preguntar(conn, tmp_path):
    """Lo que escribes se puede encontrar luego con las demás fuentes (no se pierde en un cajón)."""
    e = es.crear_escrito(conn, conn.plan, "T", "ensayo")
    es.editar_seccion(conn, es.secciones(conn, e)[0]["id"], texto="La hipótesis del cinturón de asteroides es mi tesis central.")
    assert es.progreso(conn, e)["palabras"] == 10
