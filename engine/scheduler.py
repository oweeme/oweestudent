"""Planificador cronológico y repetición espaciada (SM-2)."""
from calendar import monthrange
from datetime import date, timedelta


def sm2(calidad: int, repeticiones: int, intervalo: int, ef: float):
    """calidad 0-5 (0 = olvidado total, 5 = perfecto). Devuelve (rep, intervalo, ef, fecha)."""
    if calidad < 3:
        repeticiones, intervalo = 0, 1
    else:
        intervalo = 1 if repeticiones == 0 else 6 if repeticiones == 1 else round(intervalo * ef)
        repeticiones += 1
    ef = max(1.3, ef + 0.1 - (5 - calidad) * (0.08 + (5 - calidad) * 0.02))
    return repeticiones, intervalo, ef, (date.today() + timedelta(days=intervalo)).isoformat()


def _add_months(d: date, m: int) -> date:
    y, mo = divmod(d.month - 1 + m, 12)
    return d.replace(year=d.year + y, month=mo + 1, day=min(d.day, monthrange(d.year + y, mo + 1)[1]))


def programar_temas(unidad: dict, temas_ids: list[int], inicio: date, dias_estudio=(0, 1, 2, 3, 4)):
    """Reparte los temas de una unidad entre sus meses (mes_ini..mes_fin) en días de estudio.

    Devuelve [(tema_id, 'YYYY-MM-DD')]. Sin meses definidos usa 30 días desde `inicio`.
    """
    if not temas_ids:
        return []
    if unidad.get("mes_ini") and unidad.get("mes_fin"):
        desde = _add_months(inicio, unidad["mes_ini"] - 1)
        hasta = _add_months(inicio, unidad["mes_fin"])
    else:
        desde, hasta = inicio, inicio + timedelta(days=30)
    dias, d = [], desde
    while d < hasta:
        if d.weekday() in dias_estudio:
            dias.append(d)
        d += timedelta(days=1)
    dias = dias or [desde]
    n = len(temas_ids)
    return [(tid, dias[min(len(dias) - 1, i * len(dias) // n)].isoformat())
            for i, tid in enumerate(temas_ids)]
