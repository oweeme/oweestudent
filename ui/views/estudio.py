import threading
import time

import flet as ft

from database import repo
from engine import ai, tarjetas as tj
from engine import nivel as niveles
from i18n import marcar, t, tn

FASES = (marcar("Estudio"), marcar("Descanso"))   # nombres de fase (se traducen al mostrarlos)


def build(st):
    """Pomodoro con registro automático + Feynman (escribir antes de repasar)."""
    tema = ft.Text(st.tema_titulo or t("Elige un tema desde «Plan» u «Hoy»"), weight=ft.FontWeight.BOLD)
    mins_estudio, mins_descanso = niveles.ajustes(st.nivel())["pomodoro"]      # un niño de primaria no estudia 25 min seguidos
    fases = (("Estudio", mins_estudio), ("Descanso", mins_descanso))
    reloj = ft.Text(f"{mins_estudio:02d}:00", size=48)
    fase = ft.Text(t("Estudio"))
    corriendo = {"on": False, "gen": 0}

    def ciclo(gen):
        for nombre, mins in fases:
            fase.value = t(nombre)
            for s in range(mins * 60, -1, -1):
                if not corriendo["on"] or corriendo["gen"] != gen:
                    return
                reloj.value = f"{s // 60:02d}:{s % 60:02d}"
                st.page.update()
                time.sleep(1)
            if nombre == "Estudio":
                repo.registrar_sesion(st.conn, st.tema_id, mins_estudio)
                st.toast(t("Pomodoro registrado (+{n} min)", n=mins_estudio))
        corriendo["on"] = False

    def iniciar(_):
        if not st.tema_id:
            st.toast(t("Primero elige un tema"))
            return
        corriendo["on"], corriendo["gen"] = True, corriendo["gen"] + 1
        threading.Thread(target=ciclo, args=(corriendo["gen"],), daemon=True).start()

    def parar(_):
        corriendo["on"] = False

    resumen = ft.TextField(label=t("Explícalo con tus palabras (Feynman / Active Recall)"),
                           multiline=True, min_lines=5)
    calidad = ft.Slider(min=0, max=5, divisions=5, value=3, label="{value}")

    def guardar(_):
        if not st.tema_id or not resumen.value.strip():
            st.toast(t("Elige un tema y escribe tu resumen"))
            return
        prox = repo.guardar_nota(st.conn, st.tema_id, resumen.value.strip(), int(calidad.value))
        resumen.value = ""
        st.toast(t("Repaso programado: {fecha}", fecha=prox))
        st.page.update()

    feedback = ft.Text("", selectable=True)
    apuntes = ft.TextField(label=t("Tus apuntes o material del tema (pega texto; usa **negritas** para términos clave)"),
                           multiline=True, min_lines=4, max_lines=10)
    q_manual, r_manual = ft.TextField(label=t("Pregunta")), ft.TextField(label=t("Respuesta"))
    info_tj = ft.Text("")

    def _tema_ok():
        if not st.tema_id:
            st.toast(t("Primero elige un tema"))
        return bool(st.tema_id)

    def tj_offline(_):
        if not _tema_ok():
            return
        n = repo.crear_tarjetas(st.conn, st.tema_id, tj.desde_apuntes(apuntes.value), "apuntes")
        info_tj.value = tn(n, "{n} tarjeta creada (sin IA). Se repasa en «Repaso».", "{n} tarjetas creadas (sin IA). Se repasan en «Repaso».") if n else \
            t("No detecté definiciones. Usa el formato «Término: explicación» o **negritas**.")
        st.page.update()

    def tj_ia(_):
        if not _tema_ok():
            return
        if not ai.ia_disponible():
            info_tj.value = t("Configura la IA local en Ajustes.")
        elif not apuntes.value.strip():
            info_tj.value = t("Pega primero tus apuntes.")
        else:
            info_tj.value = t("Generando tarjetas…")
            st.page.update()

            def hacer():
                try:
                    n = repo.crear_tarjetas(st.conn, st.tema_id,
                                            ai.tarjetas_desde_material(st.tema_titulo, apuntes.value), "ia")
                    info_tj.value = tn(n, "{n} tarjeta creada con IA. Revísala: un modelo pequeño puede fallar.", "{n} tarjetas creadas con IA. Revísalas: un modelo pequeño puede fallar.")
                except Exception as ex:
                    info_tj.value = t("Error IA: {ex}", ex=ex)
                st.page.update()
            threading.Thread(target=hacer, daemon=True).start()
        st.page.update()

    def tj_manual(_):
        if _tema_ok() and q_manual.value.strip() and r_manual.value.strip():
            repo.crear_tarjeta(st.conn, st.tema_id, q_manual.value, r_manual.value)
            q_manual.value = r_manual.value = ""
            info_tj.value = t("Tarjeta añadida")
            st.page.update()

    def evaluar(_):
        if not ai.ia_disponible():
            feedback.value = t("Configura la IA en Ajustes para usar esta función.")
        elif not st.tema_titulo:
            feedback.value = t("Elige primero un tema.")
        else:
            feedback.value = t("Evaluando…")
            st.page.update()

            def hacer():
                try:
                    feedback.value = t("Preguntas para comprobarte (verifica las respuestas en tu material):") + "\n" + ai.preguntas_repaso(st.tema_titulo, resumen.value)
                except Exception as ex:
                    feedback.value = t("Error IA: {ex}", ex=ex)
                st.page.update()
            threading.Thread(target=hacer, daemon=True).start()
        st.page.update()

    return ft.Column([
        ft.Text(t("Estudiar"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL), tema,
        ft.Row([reloj, fase], alignment=ft.MainAxisAlignment.START),
        ft.Row([ft.ElevatedButton(t("Iniciar Pomodoro"), icon=ft.Icons.PLAY_ARROW, on_click=iniciar),
                ft.OutlinedButton(t("Detener"), icon=ft.Icons.STOP, on_click=parar)]),
        ft.Divider(), resumen, ft.Text(t("¿Qué tan bien lo recordaste? (0 nada – 5 perfecto)")), calidad,
        ft.Divider(), ft.Text(t("Tarjetas de repaso (tú creas las preguntas)"), weight=ft.FontWeight.BOLD),
        apuntes, ft.Row([ft.ElevatedButton(t("Crear tarjetas de mis apuntes"), icon=ft.Icons.STYLE, on_click=tj_offline),
                         ft.OutlinedButton(t("✨ Con IA"), on_click=tj_ia)], wrap=True),
        ft.Row([q_manual, r_manual], wrap=True), ft.TextButton(t("＋ Añadir tarjeta manual"), on_click=tj_manual), info_tj,
        ft.Divider(),
        ft.Row([ft.ElevatedButton(t("Guardar y programar repaso"), icon=ft.Icons.SAVE, on_click=guardar),
                ft.OutlinedButton(t("✨ Preguntas de repaso (IA)"), on_click=evaluar)], wrap=True), feedback,
    ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
