"""SQLite: plan de estudios, recursos, entregables, sesiones y repaso espaciado."""
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Para sincronizar con Syncthing, apunta OWEE_DB a una carpeta sincronizada.
DATOS = Path(os.environ.get("FLET_APP_STORAGE_DATA") or Path.home() / ".oweestudent")  # Android: carpeta de la app
DB_PATH = os.environ.get("OWEE_DB", str(DATOS / "estudios.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS perfiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    nivel TEXT DEFAULT 'universitario'
);
CREATE TABLE IF NOT EXISTS carpetas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    perfil_id INTEGER DEFAULT 1,
    nombre TEXT NOT NULL,
    orden INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS materiales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER REFERENCES planes(id) ON DELETE CASCADE,
    unidad_id INTEGER REFERENCES unidades(id) ON DELETE SET NULL,
    tema_id INTEGER REFERENCES temas(id) ON DELETE SET NULL,
    titulo TEXT NOT NULL,
    tipo TEXT,
    hash TEXT,
    nombre_archivo TEXT,
    ruta TEXT,
    tam INTEGER DEFAULT 0,
    pagina_actual INTEGER DEFAULT 1,
    paginas INTEGER DEFAULT 0,
    creado DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS notas_material (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER REFERENCES materiales(id) ON DELETE CASCADE,
    pagina INTEGER DEFAULT 1,
    tipo TEXT DEFAULT 'conclusion',
    texto TEXT NOT NULL,
    creado DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS planes (
    perfil_id INTEGER DEFAULT 1,
    carpeta_id INTEGER,
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    archivo TEXT,
    meta TEXT,
    fecha_inicio DATE,
    horas_semana REAL DEFAULT 12,
    creado DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS unidades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER REFERENCES planes(id) ON DELETE CASCADE,
    titulo TEXT NOT NULL,
    semestre TEXT,
    tipo TEXT DEFAULT 'modulo',
    mes_ini INTEGER, mes_fin INTEGER,
    orden INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS temas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unidad_id INTEGER REFERENCES unidades(id) ON DELETE CASCADE,
    titulo TEXT NOT NULL,
    horas_estimadas REAL DEFAULT 1.5,
    horas_dedicadas REAL DEFAULT 0,
    fecha_programada DATE,
    estado TEXT CHECK(estado IN ('pendiente','en_proceso','completado')) DEFAULT 'pendiente',
    orden INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS recursos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unidad_id INTEGER REFERENCES unidades(id) ON DELETE CASCADE,
    tipo TEXT CHECK(tipo IN ('libro','url','busqueda','alternativa','herramienta')),
    contenido TEXT NOT NULL,
    descripcion TEXT,
    leido INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS entregables (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unidad_id INTEGER REFERENCES unidades(id) ON DELETE CASCADE,
    titulo TEXT NOT NULL,
    descripcion TEXT,
    estado TEXT CHECK(estado IN ('pendiente','en_proceso','completado')) DEFAULT 'pendiente'
);
CREATE TABLE IF NOT EXISTS metas_idioma (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unidad_id INTEGER REFERENCES unidades(id) ON DELETE CASCADE,
    idioma TEXT NOT NULL,
    objetivo TEXT,
    detalle TEXT
);
CREATE TABLE IF NOT EXISTS cronograma (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER REFERENCES planes(id) ON DELETE CASCADE,
    dia TEXT NOT NULL, bloque TEXT NOT NULL, actividad TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sesiones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tema_id INTEGER REFERENCES temas(id) ON DELETE SET NULL,
    minutos REAL NOT NULL,
    fecha DATE DEFAULT (date('now','localtime'))
);
CREATE TABLE IF NOT EXISTS tarjetas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tema_id INTEGER REFERENCES temas(id) ON DELETE CASCADE,
    pregunta TEXT NOT NULL,
    respuesta TEXT NOT NULL,
    origen TEXT DEFAULT 'manual',
    proximo_repaso DATE DEFAULT (date('now','localtime')),
    intervalo_dias INTEGER DEFAULT 0,
    repeticiones INTEGER DEFAULT 0,
    factor_facilidad REAL DEFAULT 2.5,
    creado DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS repasos_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tema_id INTEGER, tipo TEXT, calidad INTEGER,
    fecha DATE DEFAULT (date('now','localtime'))
);
CREATE TABLE IF NOT EXISTS notas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tema_id INTEGER REFERENCES temas(id) ON DELETE CASCADE,
    resumen_propio TEXT NOT NULL,
    dificultad INTEGER CHECK(dificultad BETWEEN 0 AND 5),
    proximo_repaso DATE,
    intervalo_dias INTEGER DEFAULT 0,
    repeticiones INTEGER DEFAULT 0,
    factor_facilidad REAL DEFAULT 2.5,
    creado DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


# Tablas que se sincronizan entre equipos (la mezcla usa uid + fecha de modificación)
TABLAS_SYNC = ["perfiles", "carpetas", "planes", "unidades", "temas", "recursos", "entregables", "metas_idioma",
               "cronograma", "materiales", "notas_material", "sesiones", "notas", "tarjetas", "repasos_log"]
_AHORA = "strftime('%Y-%m-%dT%H:%M:%f','now')"
_LEGADO = "2000-01-01T00:00:00.000"  # filas anteriores a la sincronización: cualquier edición real las supera


@contextmanager
def sin_triggers(conn):
    """Para cambios locales que no deben contar como edición sincronizable (p. ej. la ruta de un archivo)."""
    conn.execute("UPDATE _sync SET activo=1")
    try:
        yield
    finally:
        conn.execute("UPDATE _sync SET activo=0")


def migrar_sync(conn):
    """Añade uid + modificado a cada tabla y triggers que los mantienen (el resto del código no cambia)."""
    conn.execute("CREATE TABLE IF NOT EXISTS _sync (activo INTEGER NOT NULL)")
    if not conn.execute("SELECT 1 FROM _sync").fetchone():
        conn.execute("INSERT INTO _sync VALUES (0)")
    conn.execute("CREATE TABLE IF NOT EXISTS _tombstones (tabla TEXT, uid TEXT, modificado TEXT, PRIMARY KEY(tabla, uid))")
    for t in TABLAS_SYNC:
        cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({t})")]
        for col in ("uid", "modificado"):
            if col not in cols:
                conn.execute(f"ALTER TABLE {t} ADD COLUMN {col} TEXT")
        cuando = "WHEN (SELECT activo FROM _sync)=0"
        conn.execute(f"""CREATE TRIGGER IF NOT EXISTS {t}_sync_ai AFTER INSERT ON {t} {cuando}
            BEGIN UPDATE {t} SET uid=COALESCE(uid, lower(hex(randomblob(16)))), modificado={_AHORA} WHERE id=NEW.id; END""")
        conn.execute(f"""CREATE TRIGGER IF NOT EXISTS {t}_sync_au AFTER UPDATE ON {t}
            WHEN (SELECT activo FROM _sync)=0 AND NEW.modificado IS OLD.modificado
            BEGIN UPDATE {t} SET modificado={_AHORA} WHERE id=NEW.id; END""")
        conn.execute(f"""CREATE TRIGGER IF NOT EXISTS {t}_sync_ad AFTER DELETE ON {t} {cuando}
            BEGIN INSERT OR REPLACE INTO _tombstones VALUES ('{t}', OLD.uid, {_AHORA}); END""")
        conn.execute("UPDATE _sync SET activo=1")  # rellena filas antiguas sin disparar los triggers
        conn.execute(f"UPDATE {t} SET uid='legacy-{t}-'||id, modificado='{_LEGADO}' WHERE uid IS NULL")
        conn.execute("UPDATE _sync SET activo=0")
        conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS idx_{t}_uid ON {t}(uid)")


def connect(db_path: str = DB_PATH) -> sqlite3.Connection:
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = connect(db_path)
    conn.executescript(SCHEMA)
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(planes)")]
    if "perfil_id" not in cols:  # migración de bases creadas antes de los perfiles
        conn.execute("ALTER TABLE planes ADD COLUMN perfil_id INTEGER DEFAULT 1")
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(perfiles)")]
    for col in ("clave_hash", "sal"):
        if col not in cols:
            conn.execute(f"ALTER TABLE perfiles ADD COLUMN {col} TEXT")
    if "carpeta_id" not in [r["name"] for r in conn.execute("PRAGMA table_info(planes)")]:
        conn.execute("ALTER TABLE planes ADD COLUMN carpeta_id INTEGER")
    for tabla in ("tarjetas", "notas"):  # estado FSRS
        cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({tabla})")]
        for col, tipo in (("estabilidad", "REAL"), ("dificultad_fsrs", "REAL"), ("ultimo_repaso", "DATE")):
            if col not in cols:
                conn.execute(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}")
    if not conn.execute("SELECT 1 FROM perfiles").fetchone():
        conn.execute("INSERT INTO perfiles(id, nombre) VALUES (1, 'Yo')")
    migrar_sync(conn)
    # cronograma duplicado por importar dos veces el mismo plan: se conserva la primera fila de cada grupo
    conn.execute("""DELETE FROM cronograma WHERE id NOT IN
                    (SELECT MIN(id) FROM cronograma GROUP BY plan_id, dia, bloque, actividad)""")
    conn.commit()
    return conn
