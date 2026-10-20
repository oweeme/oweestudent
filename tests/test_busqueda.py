"""Preguntar a tus documentos: tokenización, índice, ranking con citas y revisión de la respuesta."""
import pytest

from database import db, repo
from engine import busqueda as bq
from engine import material as mat

LIBRO = """# Educación rural

La educación rural en Bolivia enfrenta la escasez de maestros y la distancia entre las escuelas y las comunidades.

Los estudios de caso permiten comprender la realidad de cada comunidad con mucho detalle y contexto.

""" + "\n\n".join(f"Párrafo de relleno número {i} sobre metodología general de la investigación social y sus técnicas "
                  "habituales, sin relación con el resto de los temas tratados en este texto de prueba." for i in range(8)) + """

Capítulo dos. La fotosíntesis es el proceso por el cual las plantas convierten la luz solar en energía química.

Las mitocondrias producen energía para la célula mediante la respiración celular.
"""


@pytest.fixture
def entorno(tmp_path):
    conn = db.init_db(":memory:")
    plan = repo.crear_plan(conn, "Tesis", 1)
    f = tmp_path / "libro.md"
    f.write_text(LIBRO, encoding="utf-8")
    h = mat.hash_archivo(str(f))
    mid = repo.agregar_material(conn, plan, "Libro de campo", "md", h, "libro.md", str(f), f.stat().st_size)
    return conn, plan, mid, h, str(f), bq.Indice(tmp_path / "indice.db")


def test_tokenizar_ignora_acentos_mayusculas_y_palabras_vacias():
    assert bq.tokenizar("La EDUCACIÓN de los niños") == bq.tokenizar("educacion niños")
    assert "de" not in bq.tokenizar("el libro de la casa") and "the" not in bq.tokenizar("the book of the house")
    assert bq.tokenizar("informar") == bq.tokenizar("información")
    assert bq.tokenizar("redes") == bq.tokenizar("red") == ["red"]


def test_tokenizar_raiz_simple_une_plurales_y_formas():
    assert bq.tokenizar("estudios")[0] == bq.tokenizar("estudio")[0]
    assert bq.tokenizar("comunidades")[0] == bq.tokenizar("comunidad")[0]
    assert bq.tokenizar("educación") [0] == bq.tokenizar("educaciones")[0]


def test_tokenizar_chino_y_japones_en_pares_de_caracteres():
    assert bq.tokenizar("机器学习") == ["机器", "器学", "学习"]
    assert bq.tokenizar("日本語") == ["日本", "本語"]
    assert bq.tokenizar("A 学") == ["学"]


def test_trocear_respeta_parrafos_y_tamano():
    texto = "Primer párrafo con bastante texto para pasar el mínimo.\n\nSegundo párrafo también con suficiente texto."
    assert len(bq.trocear(texto)) == 1 and len(bq.trocear(texto, 60)) == 2
    largo = ". ".join(f"Frase número {i} con palabras de relleno suficientes" for i in range(60))
    assert all(len(p) <= bq.MAX_PASAJE * 2 for p in bq.trocear(largo)) and len(bq.trocear(largo)) > 2
    assert bq.trocear("corto") == []


def test_indexar_una_sola_vez_y_buscar_con_pagina(entorno):
    conn, plan, mid, h, ruta, idx = entorno
    assert [m["id"] for m in bq.materiales_pendientes(conn, idx, [plan])] == [mid]
    assert idx.indexar_material(h, ruta) > 0
    assert idx.indexar_material(h, ruta) == 0                       # ya indexado
    assert bq.materiales_pendientes(conn, idx, [plan]) == []
    r = bq.buscar(conn, idx, [plan], "¿Qué es la fotosíntesis?")
    assert r and r[0].origen == "material" and "fotosíntesis" in r[0].texto and r[0].ref_id == mid
    assert 1 <= r[0].pagina <= mat.num_paginas(ruta)
    assert "p." in r[0].etiqueta() and r[0].titulo == "Libro de campo"


def test_el_ranking_pone_primero_lo_relevante(entorno):
    conn, plan, mid, h, ruta, idx = entorno
    idx.indexar_material(h, ruta)
    r = bq.buscar(conn, idx, [plan], "maestros y escuelas en comunidades rurales de Bolivia")
    assert "maestros" in r[0].texto
    r2 = bq.buscar(conn, idx, [plan], "mitocondrias respiración celular")
    assert "mitocondrias" in r2[0].texto and r[0].texto != r2[0].texto
    assert bq.buscar(conn, idx, [plan], "criptomonedas blockchain") == []
    assert bq.buscar(conn, idx, [plan], "el de la") == []             # solo palabras vacías


def test_las_notas_y_las_fichas_tambien_son_fuentes_y_nunca_estan_viejas(entorno):
    conn, plan, mid, h, ruta, idx = entorno
    repo.agregar_nota_material(conn, mid, 1, "Mi conclusión: el rezago escolar depende del transporte", "conclusion")
    l = repo.agregar_lectura(conn, plan, "Estudio de transporte", autores="Quispe, R", anio=2021, hallazgos="El transporte escolar reduce la deserción")
    r = bq.buscar(conn, idx, [plan], "transporte escolar")
    assert {x.origen for x in r} == {"nota", "lectura"}
    assert next(x for x in r if x.origen == "lectura").ref_id == l
    repo.editar_lectura(conn, l, hallazgos="Nada relevante")
    assert all(x.origen != "lectura" for x in bq.buscar(conn, idx, [plan], "deserción"))


def test_alcance_por_asignatura(entorno, tmp_path):
    conn, plan, mid, h, ruta, idx = entorno
    otro = repo.crear_plan(conn, "Biología", 1)
    f = tmp_path / "bio.md"
    f.write_text("La meiosis produce gametos con la mitad de cromosomas que la célula original en organismos diploides.\n" * 3)
    hb = mat.hash_archivo(str(f))
    repo.agregar_material(conn, otro, "Apuntes de biología", "md", hb, "bio.md", str(f), 10)
    idx.indexar_material(h, ruta), idx.indexar_material(hb, str(f))
    assert bq.buscar(conn, idx, [plan], "meiosis gametos cromosomas") == []
    r = bq.buscar(conn, idx, [plan, otro], "meiosis gametos cromosomas")
    assert r and r[0].titulo == "Apuntes de biología" and r[0].plan_id == otro


def test_mismo_archivo_en_dos_asignaturas_se_indexa_una_vez(entorno):
    conn, plan, mid, h, ruta, idx = entorno
    otro = repo.crear_plan(conn, "Otra", 1)
    repo.agregar_material(conn, otro, "Libro (copia)", "md", h, "libro.md", ruta, 10)
    assert len(bq.materiales_pendientes(conn, idx, [plan, otro])) == 1


def test_archivo_que_no_esta_en_este_equipo_no_se_intenta_indexar(entorno):
    conn, plan, mid, h, ruta, idx = entorno
    conn.execute("UPDATE materiales SET ruta=NULL"); conn.commit()
    assert bq.materiales_pendientes(conn, idx, [plan]) == []


def test_revisar_respuesta_quita_citas_inventadas_y_avisa():
    ok = bq.revisar_respuesta("Faltan maestros [1]. Hay distancia [2][1]. Y es grave [7].", 2)
    assert ok["citas"] == [1, 2] and "[7]" not in ok["texto"] and ok["encontrada"] and not ok["sin_citas"]
    assert bq.revisar_respuesta("Una respuesta sin citas.", 3)["sin_citas"] is True
    no = bq.revisar_respuesta("NO_ENCONTRADO", 3)
    assert no == {"texto": "", "citas": [], "encontrada": False, "sin_citas": False}
    assert bq.revisar_respuesta("", 3)["encontrada"] is False


def test_responder_con_ia_inyectada_y_copia_con_citas(entorno):
    conn, plan, mid, h, ruta, idx = entorno
    idx.indexar_material(h, ruta)
    fuentes = bq.buscar(conn, idx, [plan], "¿Qué dificultades tiene la educación rural?")
    vistos = {}

    def falso(prompt, sistema, max_tokens):
        vistos.update(prompt=prompt, sistema=sistema)
        return "Faltan maestros y hay mucha distancia [1]. Dato inventado [9]."
    r = bq.responder("¿Qué dificultades tiene la educación rural?", fuentes, llm=falso)
    assert "[1]" in vistos["prompt"] and "FRAGMENTOS" in vistos["prompt"] and "SOLO" in vistos["sistema"]
    assert r["citas"] == [1] and "[9]" not in r["texto"]
    txt = bq.con_citas(r, fuentes)
    assert txt.startswith("Faltan maestros") and "[1] Libro de campo" in txt


def test_prompt_recorta_los_fragmentos_para_caber_en_un_modelo_pequeno():
    f = [bq.Fuente("material", "L", 1, "x" * 5000, ref_id=1)]
    assert len(bq.prompt_respuesta("¿?", f)) < 1000
