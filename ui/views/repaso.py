import flet as ft

from database import repo


def build(st):
    col = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def cargar():
        col.controls.clear()
        col.controls.append(ft.Text("Repaso", style=ft.TextThemeStyle.HEADLINE_SMALL))
        tj = repo.tarjetas_pendientes(st.conn, st.perfil_id)
        notas = repo.repasos_pendientes(st.conn, st.perfil_id)
        if not tj and not notas:
            col.controls.append(ft.Text("No tienes repasos pendientes hoy 🎉 "
                                        "Crea tarjetas desde tus apuntes en «Estudiar»."))
        if tj:
            col.controls += [ft.Text(f"Tarjetas pendientes: {len(tj)}", weight=ft.FontWeight.BOLD),
                             _card(tj[0]["pregunta"], tj[0]["respuesta"], tj[0]["tema"],
                                   lambda q, i=tj[0]["id"]: (repo.repasar_tarjeta(st.conn, i, q), cargar()))]
        if notas:
            col.controls.append(ft.Text(f"Resúmenes (Feynman) pendientes: {len(notas)}", weight=ft.FontWeight.BOLD))
            for n in notas[:5]:
                col.controls.append(_card(f"Explica con tus palabras: {n['tema']}", n["resumen_propio"], n["tema"],
                                          lambda q, i=n["id"]: (repo.repasar(st.conn, i, q), cargar())))
        st.page.update()

    def _card(pregunta, respuesta, tema, calificar):
        resp = ft.Text(respuesta, visible=False, selectable=True, size=15)
        botones = ft.Row([ft.OutlinedButton(str(q), on_click=lambda _, q=q: calificar(q)) for q in range(6)],
                         visible=False, wrap=True)
        leyenda = ft.Text("¿Qué tan bien lo recordaste? 0 = nada · 3 = con esfuerzo · 5 = perfecto", size=12,
                          visible=False)

        def mostrar(_):
            resp.visible = botones.visible = leyenda.visible = True
            st.page.update()

        return ft.Card(content=ft.Container(padding=14, content=ft.Column([
            ft.Text(tema, size=12, color=ft.Colors.BLUE_200), ft.Text(pregunta, size=17, weight=ft.FontWeight.W_500),
            ft.TextButton("Mostrar respuesta (intenta recordar primero)", on_click=mostrar), resp, leyenda, botones])))

    cargar()
    return col
