"""Mezcla dos bases de OweeStudent: gana el cambio más reciente de cada registro (last-write-wins).

Cada fila tiene uid (identidad global) y `modificado` (UTC). Los borrados viajan como lápidas (_tombstones).
Las filas con clave foránea se re-enlazan por uid porque los ids enteros difieren entre equipos.
"""
import shutil
import sqlite3
import tempfile
from pathlib import Path

from database.db import TABLAS_SYNC, init_db

# tabla -> {columna FK: (tabla padre, obligatoria)}. Si un padre opcional no existe aquí, la columna queda NULL.
FK = {"carpetas": {"perfil_id": ("perfiles", True)},
      "planes": {"perfil_id": ("perfiles", True), "carpeta_id": ("carpetas", False)},
      "unidades": {"plan_id": ("planes", True)}, "temas": {"unidad_id": ("unidades", True)},
      "recursos": {"unidad_id": ("unidades", True)}, "entregables": {"unidad_id": ("unidades", True)},
      "metas_idioma": {"unidad_id": ("unidades", True)}, "cronograma": {"plan_id": ("planes", True)},
      "materiales": {"plan_id": ("planes", True), "unidad_id": ("unidades", False), "tema_id": ("temas", False)},
      "notas_material": {"material_id": ("materiales", True)},
      "sesiones": {"tema_id": ("temas", False)}, "notas": {"tema_id": ("temas", True)},
      "tarjetas": {"tema_id": ("temas", True)}, "repasos_log": {"tema_id": ("temas", False)}}
NO_PISAR = {"perfiles": {"clave_hash", "sal"}, "materiales": {"ruta"}}  # una mezcla nunca cambia la clave de un perfil ni la ruta local de un archivo
NULL_EN_INSERT = {"materiales": ("ruta",)}  # la ruta del otro equipo no sirve aquí
INMUTABLES = {"sesiones", "repasos_log"}  # solo se añaden


def es_virgen(conn) -> bool:
    """Base recién creada: sin planes, tarjetas, notas ni más de un perfil."""
    q = lambda t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    return q("planes") == 0 and q("notas") == 0 and q("tarjetas") == 0 and q("perfiles") <= 1


def fusionar(local: sqlite3.Connection, ruta_remota: str) -> dict:
    """Mezcla `ruta_remota` dentro de la conexión `local`. Devuelve contadores."""
    with tempfile.TemporaryDirectory() as d:
        copia = Path(d) / "r.db"
        shutil.copy(ruta_remota, copia)
        remota = init_db(str(copia))  # migra bases antiguas (uid/modificado) antes de mezclar
        try:
            return _fusionar(local, remota)
        finally:
            remota.close()


def _fusionar(L, R) -> dict:
    st = {"nuevos": 0, "actualizados": 0, "borrados": 0}
    L.execute("UPDATE _sync SET activo=1")  # desactiva triggers: se conservan uid/modificado remotos
    try:
        lapidas_L = {(t, u): m for t, u, m in L.execute("SELECT tabla, uid, modificado FROM _tombstones")}
        for tabla in TABLAS_SYNC:
            cols_R = [r["name"] for r in R.execute(f"PRAGMA table_info({tabla})")]
            cols_L = {r["name"] for r in L.execute(f"PRAGMA table_info({tabla})")}
            cols = [c for c in cols_R if c in cols_L and c != "id"]
            fks = FK.get(tabla, {})
            for fila in R.execute(f"SELECT * FROM {tabla}"):
                valores = {c: fila[c] for c in cols}
                ok = True
                for col, (padre, obligatorio) in fks.items():
                    rid = fila[col]
                    if rid is None:
                        continue
                    puid = R.execute(f"SELECT uid FROM {padre} WHERE id=?", (rid,)).fetchone()
                    lid = L.execute(f"SELECT id FROM {padre} WHERE uid=?", (puid[0],)).fetchone() if puid else None
                    if lid is None:
                        if obligatorio:
                            ok = False  # el padre no existe aquí (p. ej. fue borrado): se omite el hijo
                            break
                        valores[col] = None
                        continue
                    valores[col] = lid[0]
                if not ok:
                    continue
                local_fila = L.execute(f"SELECT id, modificado FROM {tabla} WHERE uid=?", (fila["uid"],)).fetchone()
                if local_fila is None:
                    lap = lapidas_L.get((tabla, fila["uid"]))
                    if lap and lap >= (fila["modificado"] or ""):
                        continue  # aquí se borró después de la última edición remota
                    for col in NULL_EN_INSERT.get(tabla, ()):
                        if col in valores:
                            valores[col] = None
                    ks = list(valores)
                    L.execute(f"INSERT INTO {tabla}({','.join(ks)}) VALUES ({','.join('?' * len(ks))})",
                              [valores[k] for k in ks])
                    st["nuevos"] += 1
                elif tabla not in INMUTABLES and (fila["modificado"] or "") > (local_fila["modificado"] or ""):
                    ks = [k for k in valores if k != "uid" and k not in NO_PISAR.get(tabla, ())]
                    L.execute(f"UPDATE {tabla} SET {','.join(k + '=?' for k in ks)} WHERE id=?",
                              [valores[k] for k in ks] + [local_fila["id"]])
                    st["actualizados"] += 1
        # borrados remotos: se aplican si nadie editó el registro después
        for t, uid, mod in R.execute("SELECT tabla, uid, modificado FROM _tombstones").fetchall():
            if t not in TABLAS_SYNC:
                continue
            fila = L.execute(f"SELECT id, modificado FROM {t} WHERE uid=?", (uid,)).fetchone()
            if fila and (fila["modificado"] or "") <= mod:
                L.execute(f"DELETE FROM {t} WHERE id=?", (fila["id"],))
                st["borrados"] += 1
            L.execute("INSERT OR REPLACE INTO _tombstones VALUES (?,?,?)", (t, uid, mod))
        L.execute("UPDATE _sync SET activo=0")
        L.commit()
    except Exception:
        L.rollback()
        L.execute("UPDATE _sync SET activo=0")
        L.commit()
        raise
    return st
