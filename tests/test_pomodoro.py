from engine.pomodoro import DESCANSO, ESTUDIO, Pomodoro


class Reloj:
    def __init__(self): self.t = 1000.0
    def __call__(self): return self.t


def nuevo():
    r = Reloj()
    return r, Pomodoro(r)


def test_cuenta_atras_y_barra():
    r, p = nuevo()
    p.iniciar(7, "Tema", 25, 5)
    assert p.texto() == "25:00" and p.avance() == 0
    r.t += 750
    assert p.texto() == "12:30" and abs(p.avance() - 0.5) < 1e-9


def test_pausar_congela_y_reanudar_sigue():
    r, p = nuevo()
    p.iniciar(1, "T", 10, 2)
    r.t += 60
    p.pausar()
    r.t += 3600                      # una hora «pausado»: no debe contar
    assert p.texto() == "09:00" and p.avanzar() == []
    p.reanudar()
    r.t += 60
    assert p.texto() == "08:00"


def test_al_acabar_el_estudio_registra_y_pasa_al_descanso_y_luego_termina():
    r, p = nuevo()
    p.iniciar(3, "T", 1, 1)
    r.t += 59
    assert p.avanzar() == []
    r.t += 1
    assert p.avanzar() == [("estudio_completo", 3, 1)] and p.fase == DESCANSO and p.activo
    assert p.avanzar() == []         # no se repite el evento
    r.t += 60
    assert p.avanzar() == [("fin",)] and not p.activo


def test_detener_y_estado_inicial():
    r, p = nuevo()
    assert not p.activo and p.restante() == 0 and p.fase == ESTUDIO
    p.iniciar(1, "T")
    p.detener()
    assert not p.activo and p.avanzar() == []
