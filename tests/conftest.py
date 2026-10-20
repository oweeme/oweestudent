import os
import sys
import tempfile
from pathlib import Path

# Las pruebas nunca tocan tus datos reales (~/.oweestudent): base y configuración en una carpeta temporal.
# Debe ir antes de importar la app, que lee estas variables al cargarse.
_TMP = tempfile.mkdtemp(prefix="oweestudent-pruebas-")
os.environ["FLET_APP_STORAGE_DATA"] = _TMP
os.environ["OWEE_DB"] = os.path.join(_TMP, "estudios.db")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
EJEMPLO = Path(__file__).resolve().parents[1] / "ejemplos" / "plan_ejemplo.md"


class Con:
    """Conexión con atajos de prueba (`plan`, `tema`…): sqlite3.Connection no admite atributos nuevos."""

    def __init__(self, c, **atajos):
        self._c = c
        self.__dict__.update(atajos)

    def __getattr__(self, nombre):
        return getattr(self._c, nombre)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _idioma_limpio():
    """Ninguna prueba hereda el idioma (ni la escritura Owee) de la anterior."""
    import i18n
    i18n.fijar_idioma("es")
    i18n.fijar_escritura_owee(False)
    yield
    i18n.fijar_idioma("es")
    i18n.fijar_escritura_owee(False)
