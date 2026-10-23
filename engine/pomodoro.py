"""Pomodoro que sigue corriendo mientras navegas: el estado vive aquí (no en una pantalla) y se calcula con un reloj,
así que no se desfasa aunque la interfaz esté ocupada. La pantalla solo lo dibuja."""
import time

ESTUDIO, DESCANSO = "Estudio", "Descanso"


class Pomodoro:
    def __init__(self, reloj=time.monotonic):
        self._reloj = reloj
        self.activo = False
        self.pausado = False
        self.fase = ESTUDIO
        self.tema_id = None
        self.titulo = ""
        self.mins = {ESTUDIO: 25, DESCANSO: 5}
        self._fin = 0.0          # instante en que acaba la fase (si corre)
        self._resto = 0.0        # segundos que quedaban al pausar

    def iniciar(self, tema_id, titulo: str, mins_estudio: int = 25, mins_descanso: int = 5) -> None:
        self.activo, self.pausado, self.fase = True, False, ESTUDIO
        self.tema_id, self.titulo = tema_id, titulo
        self.mins = {ESTUDIO: mins_estudio, DESCANSO: mins_descanso}
        self._fin = self._reloj() + mins_estudio * 60

    def total(self) -> float:
        return self.mins[self.fase] * 60

    def restante(self) -> float:
        if not self.activo:
            return 0.0
        return self._resto if self.pausado else max(0.0, self._fin - self._reloj())

    def avance(self) -> float:
        """0 al empezar la fase, 1 al terminar (para la barra)."""
        return 0.0 if not self.activo or not self.total() else 1 - self.restante() / self.total()

    def texto(self) -> str:
        s = int(self.restante() + 0.999)
        return f"{s // 60:02d}:{s % 60:02d}"

    def pausar(self) -> None:
        if self.activo and not self.pausado:
            self._resto, self.pausado = self.restante(), True

    def reanudar(self) -> None:
        if self.activo and self.pausado:
            self._fin, self.pausado = self._reloj() + self._resto, False

    def detener(self) -> None:
        self.activo = self.pausado = False

    def avanzar(self) -> list[tuple]:
        """Llamar cada segundo. Devuelve los eventos ocurridos: ('estudio_completo', tema_id, minutos) al acabar el
        estudio (pasa solo al descanso) y ('fin',) al acabar el descanso."""
        if not self.activo or self.pausado or self.restante() > 0:
            return []
        if self.fase == ESTUDIO:
            self.fase, self._fin = DESCANSO, self._reloj() + self.mins[DESCANSO] * 60
            return [("estudio_completo", self.tema_id, self.mins[ESTUDIO])]
        self.detener()
        return [("fin",)]
