import flet as ft

from i18n import t


def crear(st, abrir_estudio):
    """Franja que se ve en TODAS las pantallas mientras corre un Pomodoro: cuenta atrás, línea de avance, pausa y parada.
    Devuelve el control; se actualiza sola con el reloj global."""
    texto = ft.Text("", size=13, weight=ft.FontWeight.BOLD)
    tema = ft.Text("", size=12, max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True)
    linea = ft.ProgressBar(value=0, height=6)
    pausa = ft.IconButton(ft.Icons.PAUSE, icon_size=20, tooltip=t("Pausar"))
    parar = ft.IconButton(ft.Icons.STOP, icon_size=20, tooltip=t("Detener"))
    caja = ft.Container(visible=False, padding=ft.padding.symmetric(horizontal=12, vertical=6), border_radius=10,
                        bgcolor=ft.Colors.SECONDARY_CONTAINER, on_click=lambda _: abrir_estudio(),
                        content=ft.Column([ft.Row([ft.Icon(ft.Icons.TIMER, size=18), texto, tema, pausa, parar],
                                                  vertical_alignment=ft.CrossAxisAlignment.CENTER), linea], spacing=2))

    def alternar(_):
        p = st.pomodoro
        p.reanudar() if p.pausado else p.pausar()
        st.redibujar_pomodoro()

    def detener(_):
        st.pomodoro.detener()
        st.redibujar_pomodoro()

    pausa.on_click, parar.on_click = alternar, detener

    def dibujar():
        p = st.pomodoro
        caja.visible = p.activo
        if p.activo:
            texto.value = f"{t(p.fase)} · {p.texto()}"
            tema.value = p.titulo
            linea.value = p.avance()
            pausa.icon = ft.Icons.PLAY_ARROW if p.pausado else ft.Icons.PAUSE
            pausa.tooltip = t("Reanudar") if p.pausado else t("Pausar")

    dibujar._global = True       # la pantalla Estudiar reemplaza su propio redibujado, no este
    st.al_tick.append(dibujar)
    dibujar()
    return caja
