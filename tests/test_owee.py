"""Owee como idioma de la interfaz: escritura, respaldo, vocabulario aprobado y cobertura."""
from pathlib import Path

import pytest

import i18n
from i18n import cobertura, owee
from i18n.catalogos import CATALOGOS
from i18n.catalogos.en import TEXTOS as EN

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _limpio():
    i18n.fijar_idioma("es")
    i18n.fijar_escritura_owee(False)
    yield
    i18n.fijar_idioma("es")
    i18n.fijar_escritura_owee(False)


def test_romano_a_escritura_y_vuelta():
    s = owee.a_escritura("sade-kelo Ana 2026")
    assert owee.tiene_glifos(s) and owee.NEXO in s and owee.NOMBRE in s
    assert owee.a_romano(s) == "sade-kelo Ana 2026"


def test_palabra_imposible_se_deja_en_romano():
    assert owee.a_escritura("Save") == "Save"          # «v» no existe en Owee
    assert not owee.valida("hola") and owee.valida("kelo") and not owee.valida("ki")


def test_los_marcadores_no_se_convierten():
    s = owee.a_escritura_con_marcadores("dare {fecha} kelo {n}")
    assert "{fecha}" in s and "{n}" in s
    assert owee.tiene_glifos(s.replace("{fecha}", "").replace("{n}", ""))


def test_interfaz_owee_en_romano_y_en_escritura():
    i18n.fijar_idioma("qow")
    assert i18n.t("Guardar") == "mena-fena"
    i18n.fijar_escritura_owee(True)
    assert i18n.escritura_owee()
    guardar = i18n.t("Guardar")
    assert owee.tiene_glifos(guardar) and owee.a_romano(guardar) == "mena-fena"


def test_lo_que_falta_en_owee_se_ve_en_ingles_sin_convertir():
    i18n.fijar_idioma("qow")
    i18n.fijar_escritura_owee(True)
    assert i18n.t("Cancelar") != "Cancel"               # sí está
    assert i18n.t("Planes pendientes de hoy") == "Planes pendientes de hoy"   # ni en inglés: español
    assert i18n.t("Ajustes") != "Settings"
    assert i18n.t("Importar aquí") == "Import here"     # falta en Owee: inglés, nunca glifos inventados
    assert not owee.tiene_glifos(i18n.t("Importar aquí"))


def test_la_escritura_owee_solo_afecta_al_idioma_owee():
    i18n.fijar_escritura_owee(True)
    i18n.fijar_idioma("en")
    assert i18n.t("Guardar") == "Save" and not i18n.escritura_owee()


def test_variables_y_numeros_no_pasan_a_glifos():
    i18n.fijar_idioma("qow")
    i18n.fijar_escritura_owee(True)
    assert i18n.t("{n} días", n=3) == "3 días"      # no está en Owee ni en inglés (es un plural): español
    assert not owee.tiene_glifos(i18n.t("Error: {ex}", ex="boom"))


def vocabulario():
    return set((RAIZ / "i18n/datos/owee_vocabulario.txt").read_text(encoding="utf-8").split())


def test_el_catalogo_owee_solo_usa_palabras_aprobadas():
    """La app no inventa palabras: todo lo que dice en Owee sale del glosario/léxico del idioma."""
    vocab = vocabulario()
    for es, o in CATALOGOS["qow"].items():
        for palabra in o.split():
            assert palabra in vocab, f"{es!r}: «{palabra}» no está en el vocabulario aprobado"
            assert all(owee.valida(p) for p in palabra.split("-")), f"{es!r}: «{palabra}» no es V/CV"


def test_owee_no_pasa_de_lo_que_tiene_el_glosario():
    assert 20 <= len(CATALOGOS["qow"]) < len(EN)


def test_informe_de_cobertura():
    r = cobertura.informe("qow")
    assert r["total"] == len(EN) and r["traducidos"] == len(CATALOGOS["qow"])
    assert len(r["faltan"]) == r["total"] - r["traducidos"]
    cortos = [en for es, en in r["faltan"][:10]]
    assert all(len(x) <= 20 for x in cortos)            # primero lo más corto: son las etiquetas
    assert cobertura.informe("en")["faltan"] == []
    tsv = cobertura.como_tsv(r["faltan"][:3])
    assert tsv.startswith("en\tes\n") and tsv.count("\n") == 4


def test_fuente_y_licencia_incluidas():
    assert (RAIZ / "assets/fonts/OweeSans.ttf").stat().st_size > 10_000
    assert "SIL Open Font License" in (RAIZ / "assets/fonts/OFL-OweeSans.txt").read_text()


def test_la_fuente_cubre_todos_los_glifos_de_owee():
    fonttools = pytest.importorskip("fontTools.ttLib")
    cmap = fonttools.TTFont(RAIZ / "assets/fonts/OweeSans.ttf").getBestCmap()
    esperados = {ord(g) for g in "".join(owee._POR_ROMANO.values())} | {ord(owee.NEXO), ord(owee.NOMBRE)}
    assert esperados <= set(cmap)
