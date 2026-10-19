"""Traducciones: catálogos completos, variables intactas, plurales y respaldo."""
import pytest

import i18n
from i18n import extraer
from i18n.catalogos import CATALOGOS

CLAVES, ERRORES = extraer.extraer()
PLURALES = extraer.plurales()


@pytest.fixture(autouse=True)
def _volver_al_espanol():
    i18n.fijar_idioma("es")
    yield
    i18n.fijar_idioma("es")


def test_el_codigo_solo_usa_textos_literales():
    assert ERRORES == []


def test_ninguna_funcion_oculta_t():
    assert extraer.sombras() == []


@pytest.mark.parametrize("codigo", ["en"])
def test_catalogo_completo(codigo):
    faltan = [k for k in CLAVES if k not in CATALOGOS[codigo]]
    assert faltan == [], f"faltan en {codigo}: {faltan[:5]}"


@pytest.mark.parametrize("codigo", sorted(CATALOGOS))
def test_catalogo_sin_claves_huerfanas_ni_vacias(codigo):
    huerfanas = [k for k in CATALOGOS[codigo] if k not in CLAVES]
    assert huerfanas == [], f"claves que ya no existen en el código: {huerfanas[:5]}"
    assert all(v for v in CATALOGOS[codigo].values())


@pytest.mark.parametrize("codigo", sorted(CATALOGOS))
def test_mismas_variables_que_el_original(codigo):
    for k, v in CATALOGOS[codigo].items():
        for forma in (v if isinstance(v, tuple) else (v,)):
            if "{n}" in k and isinstance(v, tuple) and forma is v[0]:
                continue   # el singular puede escribir «un» en vez de {n}; no hay ese caso hoy, pero se permite
            assert extraer.variables(forma) == extraer.variables(k), f"{codigo}: {k[:60]}"


@pytest.mark.parametrize("codigo", sorted(CATALOGOS))
def test_plurales_son_tuplas(codigo):
    for k, v in CATALOGOS[codigo].items():
        assert isinstance(v, tuple) == (k in PLURALES), f"{codigo}: {k[:60]}"


def test_espanol_devuelve_el_original():
    assert i18n.t("Guardar") == "Guardar"
    assert i18n.t("Hola {nombre}", nombre="Ana") == "Hola Ana"


def test_ingles_y_respaldo_al_espanol():
    i18n.fijar_idioma("en")
    assert i18n.t("Guardar") == "Save"
    assert i18n.t("Texto que nadie ha traducido") == "Texto que nadie ha traducido"
    assert i18n.t("Texto {x}", x=3) == "Texto 3"


def test_variable_que_falta_no_rompe_la_pantalla():
    assert i18n.t("Hola {nombre}") == "Hola {nombre}"


def test_plural_espanol_e_ingles():
    assert i18n.tn(1, "{n} día", "{n} días") == "1 día"
    assert i18n.tn(2, "{n} día", "{n} días") == "2 días"
    i18n.fijar_idioma("en")
    assert i18n.tn(1, "{n} día", "{n} días") == "1 day"
    assert i18n.tn(0, "{n} día", "{n} días") == "0 days"


def test_reglas_de_plural_por_idioma():
    assert [i18n.indice_plural("ru", n) for n in (1, 2, 5, 11, 21, 22, 25, 111)] == [0, 1, 2, 2, 0, 1, 2, 2]
    assert [i18n.indice_plural(c, 5) for c in ("zh", "ja", "qow")] == [0, 0, 0]
    assert i18n.indice_plural("de", 1) == 0 and i18n.indice_plural("de", 0) == 1


def test_idioma_desconocido_cae_al_espanol():
    assert i18n.fijar_idioma("xx") == "es"
    assert i18n.fijar_idioma("en") == "en"
    assert "es" in i18n.disponibles() and "en" in i18n.disponibles()


def test_detecta_el_idioma_del_sistema(monkeypatch):
    for var in ("LC_ALL", "LC_MESSAGES", "LANGUAGE"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("LANG", "en_US.UTF-8")
    assert i18n.detectar_sistema() == "en"
    monkeypatch.setenv("LANG", "fr_FR.UTF-8")      # sin traducción: español
    assert i18n.detectar_sistema() == "es"


def test_el_idioma_guardado_gana_al_del_sistema(tmp_path, monkeypatch):
    from engine import ai
    monkeypatch.setattr(ai, "CONFIG", tmp_path / "config.json")
    monkeypatch.setenv("LANG", "es_BO.UTF-8")
    ai.guardar_config(idioma="en")
    assert i18n.iniciar() == "en"


def test_los_mensajes_del_motor_se_traducen():
    from engine import sync
    i18n.fijar_idioma("en")
    ok, texto = sync.diagnosticar("127.0.0.1", 1)
    assert "network" in texto or "refused" in texto or "Something" in texto or "not open" in texto or "not connected" in texto


def test_la_interfaz_se_construye_en_todos_los_idiomas():
    """Humo: cada vista se puede importar con los textos de cada idioma."""
    import importlib
    for codigo in i18n.disponibles():
        i18n.fijar_idioma(codigo)
        for mod in ("login", "hoy", "plan", "importar", "estudio", "planes", "material", "sincronizar", "ajustes",
                    "repaso", "stats"):
            importlib.import_module(f"ui.views.{mod}")
