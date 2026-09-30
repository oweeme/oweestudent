"""FSRS-4.5 (repetición espaciada moderna) en Python puro, con los parámetros por defecto.

Predice la probabilidad de recordar cada tarjeta y programa el repaso para cuando baje al 90 %.
Calidad de la app (0-5) -> calificación FSRS: 0-2 Otra vez, 3 Difícil, 4 Bien, 5 Fácil.
"""
import math
from datetime import date, timedelta

W = [0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.031, 1.6474,
     0.1367, 1.0461, 2.1072, 0.0793, 0.3246, 1.587, 0.2272, 2.8755]
DECAY, FACTOR = -0.5, 19 / 81
RETENCION = 0.9


def _grado(calidad: int) -> int:
    return 1 if calidad <= 2 else 2 if calidad == 3 else 3 if calidad == 4 else 4


def _clamp_d(d):
    return min(10.0, max(1.0, d))


def _d0(g):
    return _clamp_d(W[4] - W[5] * (g - 3))


def recordabilidad(t_dias: float, estabilidad: float) -> float:
    return (1 + FACTOR * t_dias / estabilidad) ** DECAY


def _intervalo(s: float) -> int:
    return min(365, max(1, round(s / FACTOR * (RETENCION ** (1 / DECAY) - 1))))


def revisar(estabilidad, dificultad, ultimo_repaso, calidad: int, hoy: date | None = None) -> dict:
    """Devuelve el nuevo estado. Si `estabilidad` es None es la primera revisión."""
    hoy = hoy or date.today()
    g = _grado(calidad)
    if estabilidad is None:
        s, d = W[g - 1], _d0(g)
    else:
        t = max(0, (hoy - date.fromisoformat(ultimo_repaso)).days) if ultimo_repaso else 0
        r = recordabilidad(t, estabilidad)
        d = _clamp_d(W[7] * _d0(4) + (1 - W[7]) * (dificultad - W[6] * (g - 3)))
        if g == 1:
            s = W[11] * dificultad ** -W[12] * ((estabilidad + 1) ** W[13] - 1) * math.exp(W[14] * (1 - r))
            s = min(s, estabilidad)
        else:
            dificil = W[15] if g == 2 else 1
            facil = W[16] if g == 4 else 1
            s = estabilidad * (1 + math.exp(W[8]) * (11 - dificultad) * estabilidad ** -W[9]
                               * (math.exp(W[10] * (1 - r)) - 1) * dificil * facil)
    s = max(0.1, s)
    dias = 1 if g == 1 else _intervalo(s)
    return {"estabilidad": s, "dificultad": d, "intervalo": dias,
            "proximo": (hoy + timedelta(days=dias)).isoformat(), "ultimo": hoy.isoformat()}
