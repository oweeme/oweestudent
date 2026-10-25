import threading

import flet as ft

from database import repo
from engine import ai, sesion, tarjetas as tj
from engine import nivel as niveles
from i18n import marcar, t, tn

FASES = (marcar("Estudio"), marcar("Descanso"))   # nombres de fase (se traducen al mostrarlos)


def build(st):
    """Pomodoro con registro automático + Feynman (escribir antes de repasar)."""
    tema = ft.Text(st.tema_titulo or t("Elige un tema desde «Plan» u «Hoy»"), weight=ft.FontWeight.BOLD)
    pom = st.pomodoro
    reloj = ft.Text(pom.texto() if pom.activo else f"{niveles.ajustes(st.nivel())['pomodoro'][0]:02d}:00", size=48)
    fase = ft.Text(t(pom.fase) if pom.activo else t("Estudio"))
    linea = ft.ProgressBar(value=pom.avance(), height=8)
    btn_pausa = ft.OutlinedButton(t("Pausar"), icon=ft.Icons.PAUSE)

    def dibujar():
        p = st.pomodoro
        if p.activo:
            reloj.value, fase.value, linea.value = p.texto(), t(p.fase), p.avance()
            tema.value = p.titulo or tema.value
        else:
            reloj.value, linea.value = f"{niveles.ajustes(st.nivel())['pomodoro'][0]:02d}:00", 0
        if "refrescar" in estado_pasos and estado_pasos["pomodoro"] != (p.activo and p.tema_id == st.tema_id):
            estado_pasos["refrescar"]()
        btn_pausa.text = t("Reanudar") if p.pausado else t("Pausar")
        btn_pausa.icon = ft.Icons.PLAY_ARROW if p.pausado else ft.Icons.PAUSE

    estado_pasos = {"pomodoro": False}
    st.al_tick[:] = [f for f in st.al_tick if getattr(f, "_global", False)]      # deja solo el redibujado de la barra global
    st.al_tick.append(dibujar)

    def iniciar(_):
        if not st.tema_id:
            st.toast(t("Primero elige un tema"))
            return
        st.iniciar_pomodoro(st.tema_id, st.tema_titulo)
        refrescar_pasos()

    def pausar(_):
        p = st.pomodoro
        p.reanudar() if p.pausado else p.pausar()
        st.redibujar_pomodoro()

    def parar(_):
        st.pomodoro.detener()
        st.redibujar_pomodoro()

    btn_pausa.on_click = pausar
    dibujar()

    # ---------- sesión guiada ----------
    pasos_col = ft.Column(spacing=2)

    def refrescar_pasos(_=None):
        pom_tema = st.pomodoro.activo and st.pomodoro.tema_id == st.tema_id
        hechos = sesion.estado(st.conn, st.tema_id, pom_tema, bool((resumen.value or "").strip()))
        sig = sesion.siguiente(hechos)
        pasos_col.controls = [ft.Text(f"{'✅' if h else '⬜'} {i + 1}. {t(txt)}", size=13, weight=ft.FontWeight.BOLD if i == sig else None)
                              for i, (txt, h) in enumerate(zip(sesion.PASOS, hechos))]
        pasos_col.controls.append(ft.Text(t("¡Sesión completa! Mañana te toca repasar.") if sig is None else t("Siguiente: {paso}", paso=t(sesion.PASOS[sig])),
                                          size=12, color=ft.Colors.PRIMARY))
        estado_pasos["pomodoro"] = pom_tema
    estado_pasos["refrescar"] = refrescar_pasos

    resumen = ft.TextField(label=t("Explícalo con tus palabras (Feynman / Active Recall)"),
                           multiline=True, min_lines=5)
    resumen.on_change = lambda _: (refrescar_pasos(), st.page.update())
    calidad = ft.Slider(min=0, max=5, divisions=5, value=3, label="{value}")

    def guardar(_):
        if not st.tema_id or not resumen.value.strip():
            st.toast(t("Elige un tema y escribe tu resumen"))
            return
        prox = repo.guardar_nota(st.conn, st.tema_id, resumen.value.strip(), int(calidad.value))
        resumen.value = ""
        st.toast(t("Repaso programado: {fecha}", fecha=prox))
        refrescar_pasos()
        st.page.update()

    feedback = ft.Text("", selectable=True)
    apuntes = ft.TextField(label=t("Tus apuntes o material del tema (pega texto; usa **negritas** o {{...}} para los huecos)"),
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
        refrescar_pasos()
        st.page.update()

    def tj_huecos(_):
        if not _tema_ok():
            return
        pares = tj.huecos_automaticos(apuntes.value)
        n = repo.crear_tarjetas(st.conn, st.tema_id, pares, "huecos")
        info_tj.value = tn(n, "{n} tarjeta con hueco creada. Revísala: tapé la palabra clave de cada frase.",
                           "{n} tarjetas con huecos creadas. Revísalas: tapé la palabra clave de cada frase.") if n else \
            t("No encontré frases adecuadas. Escribe frases completas o marca los huecos con {{...}}.")
        refrescar_pasos()
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
            refrescar_pasos()
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

    refrescar_pasos()
    return ft.Column([
        ft.Text(t("Estudiar"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL), tema,
        ft.Row([reloj, fase], alignment=ft.MainAxisAlignment.START), linea,
        ft.Text(t("Puedes ir a leer o a otra pantalla: el reloj sigue corriendo y se ve arriba."), size=12),
        ft.Row([ft.ElevatedButton(t("Iniciar Pomodoro"), icon=ft.Icons.PLAY_ARROW, on_click=iniciar), btn_pausa,
                ft.OutlinedButton(t("Detener"), icon=ft.Icons.STOP, on_click=parar)], wrap=True),
        ft.Container(ft.Column([ft.Text(t("Tu sesión paso a paso"), weight=ft.FontWeight.BOLD), pasos_col], spacing=4), padding=10, border_radius=8,
                     border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT)),
        ft.Divider(), resumen, ft.Text(t("¿Qué tan bien lo recordaste? (0 nada – 5 perfecto)")), calidad,
        ft.Divider(), ft.Text(t("Tarjetas de repaso (tú creas las preguntas)"), weight=ft.FontWeight.BOLD),
        apuntes, ft.Row([ft.ElevatedButton(t("Crear tarjetas de mis apuntes"), icon=ft.Icons.STYLE, on_click=tj_offline),
                         ft.OutlinedButton(t("Con huecos automáticos"), on_click=tj_huecos),
                         ft.OutlinedButton(t("✨ Con IA"), on_click=tj_ia)], wrap=True),
        ft.Row([q_manual, r_manual], wrap=True), ft.TextButton(t("＋ Añadir tarjeta manual"), on_click=tj_manual), info_tj,
        ft.Divider(),
        ft.Row([ft.ElevatedButton(t("Guardar y programar repaso"), icon=ft.Icons.SAVE, on_click=guardar),
                ft.OutlinedButton(t("✨ Preguntas de repaso (IA)"), on_click=evaluar)], wrap=True), feedback,
    ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
