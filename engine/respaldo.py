"""Copia de seguridad completa en un archivo `.zip` y restauración.

La copia lleva la base de datos entera (todos los perfiles, planes, tarjetas, lecturas, escritos…) y, si quieres, los archivos de
material que adjuntaste. Restaurar REEMPLAZA tus datos actuales por los de la copia, después de guardar una copia de seguridad
automática de lo que había (carpeta «respaldos»).
"""
import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path

import app_info
from database import db
from i18n import t

BASE = "estudios.db"
CARPETA = "materiales"


def crear_copia(conn, destino, con_archivos: bool = True) -> dict:
    """Escribe el .zip. Devuelve {archivos, bytes}."""
    destino = Path(destino)
    n_arch = 0
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d) / BASE
        dst = sqlite3.connect(tmp)
        try:
            conn.backup(dst)
        finally:
            dst.close()
        esquema = sqlite3.connect(tmp).execute("PRAGMA user_version").fetchone()[0]
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(tmp, BASE)
            z.writestr("info.json", json.dumps({"app": app_info.NOMBRE, "version": app_info.VERSION, "esquema": esquema,
                                                "fecha": datetime.now().isoformat(timespec="seconds"), "con_archivos": con_archivos}))
            if con_archivos:
                vistos = set()
                for r in conn.execute("SELECT hash, ruta FROM materiales WHERE hash IS NOT NULL AND ruta IS NOT NULL"):
                    if r["hash"] in vistos or not os.path.exists(r["ruta"]):
                        continue
                    vistos.add(r["hash"])
                    z.write(r["ruta"], f"{CARPETA}/{r['hash']}{Path(r['ruta']).suffix}")
                    n_arch += 1
    return {"archivos": n_arch, "bytes": destino.stat().st_size}


def inspeccionar(ruta) -> dict:
    """Comprueba que es una copia de OweeStudent válida y de una versión que esta app entiende. Lanza ValueError si no."""
    try:
        z = zipfile.ZipFile(ruta)
    except (zipfile.BadZipFile, OSError) as ex:
        raise ValueError(t("Ese archivo no es una copia de seguridad de OweeStudent.")) from ex
    with z:
        if BASE not in z.namelist():
            raise ValueError(t("Ese archivo no es una copia de seguridad de OweeStudent."))
        info = json.loads(z.read("info.json")) if "info.json" in z.namelist() else {}
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d) / BASE
            tmp.write_bytes(z.read(BASE))
            try:
                c = sqlite3.connect(tmp)
                tablas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                esquema = c.execute("PRAGMA user_version").fetchone()[0]
                planes = c.execute("SELECT COUNT(*) FROM planes").fetchone()[0] if "planes" in tablas else 0
                tarjetas = c.execute("SELECT COUNT(*) FROM tarjetas").fetchone()[0] if "tarjetas" in tablas else 0
                c.close()
            except sqlite3.DatabaseError as ex:
                raise ValueError(t("Ese archivo no es una copia de seguridad de OweeStudent.")) from ex
        if not {"planes", "unidades", "temas", "notas"} <= tablas:
            raise ValueError(t("Ese archivo no es una copia de seguridad de OweeStudent."))
        if esquema > db.VERSION_ESQUEMA:
            raise ValueError(t("La copia es de una versión más nueva de OweeStudent. Actualiza la app antes de restaurarla."))
        archivos = [n for n in z.namelist() if n.startswith(CARPETA + "/") and not n.endswith("/")]
    return {"version": info.get("version", "?"), "fecha": info.get("fecha", ""), "esquema": esquema, "planes": planes, "tarjetas": tarjetas,
            "archivos": len(archivos)}


def restaurar(conn, db_path: str, ruta) -> dict:
    """Reemplaza los datos actuales por los de la copia. Antes guarda una copia automática de lo que había."""
    from engine import material
    info = inspeccionar(ruta)
    guardada = db.respaldar(conn, db_path, "antes-de-restaurar")
    with zipfile.ZipFile(ruta) as z, tempfile.TemporaryDirectory() as d:
        tmp = Path(d) / BASE
        tmp.write_bytes(z.read(BASE))
        src = sqlite3.connect(tmp)
        try:
            src.backup(conn)
        finally:
            src.close()
        conn.commit()
        n = 0
        material.CARPETA.mkdir(parents=True, exist_ok=True)
        for nombre in z.namelist():
            if nombre.startswith(CARPETA + "/") and not nombre.endswith("/") and ".." not in nombre:
                destino = material.CARPETA / Path(nombre).name
                if not destino.exists():
                    destino.write_bytes(z.read(nombre))
                    n += 1
    if db_path != ":memory:":
        db.init_db(db_path).close()                       # migra la base restaurada si es de una versión anterior
    with db.sin_triggers(conn):                           # las rutas de la copia eran las de OTRO equipo: se apuntan a los archivos recuperados
        for r in conn.execute("SELECT id, hash, nombre_archivo FROM materiales WHERE hash IS NOT NULL").fetchall():
            ext = Path(r["nombre_archivo"] or "").suffix.lower()
            propio = material.CARPETA / f"{r['hash']}{ext}"
            conn.execute("UPDATE materiales SET ruta=? WHERE id=?", (str(propio) if propio.exists() else None, r["id"]))
    conn.commit()
    return {**info, "archivos_recuperados": n, "copia_previa": str(guardada) if guardada else None}
