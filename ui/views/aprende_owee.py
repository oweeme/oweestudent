import flet as ft

from database import repo
from i18n import marcar, t, tn
from owee_curso import bloques as bl
from owee_curso import curso
from ui.components.owee_texto import glifos

MODOS = {"ambos": marcar("Glifos y romanización"), "glifos": marcar("Solo glifos"), "romano": marcar("Solo romanización")}


def build(st, recargar):
    c = st.conn
    est = {"lec": None, "modo": "ambos"}
    cuerpo = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
                       horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def plan():
        return curso.plan_del_curso(c, st.perfil_id)

    if plan():
        curso.actualizar_plan_del_curso(c, plan())      # el curso puede haber crecido desde que lo añadiste

    def asegurar_plan():
        existente = plan()
        if existente:
            return existente
        p = curso.crear_plan_del_curso(c, st.perfil_id)
        if not st.plan_id:
            st.plan_id = p
        st.toast(t("Curso añadido a tu plan de estudio"))
        return p

    def cambiar_modo(e):
        est["modo"] = e.control.value
        redibujar()

    def redibujar():
        mostrar_leccion(est["lec"]) if est["lec"] else mostrar_indice()

    # ---------- piezas ----------
    def bloque_owee(b):
        filas = []
        for linea in b["lineas"]:
            partes = []
            if est["modo"] in ("ambos", "glifos"):
                partes.append(glifos(linea, size=30))
            if est["modo"] in ("ambos", "romano"):
                partes.append(ft.Text(linea, size=15 if est["modo"] == "romano" else 13,
                                      color=None if est["modo"] == "romano" else ft.Colors.OUTLINE, selectable=True))
            filas.append(ft.Column(partes, spacing=0))
        extra = []
        if b["traduccion"]:
            tr = ft.Text(b["traduccion"], italic=True, visible=False, size=14, selectable=True)
            pista = ft.TextButton(t("Toca para ver la traducción"))

            def mostrar(_):
                tr.visible, pista.visible = True, False
                st.page.update()
            pista.on_click = mostrar
            extra = [pista, tr]
        return ft.Container(ft.Column([*filas, *extra], spacing=8), padding=12, border_radius=8,
                            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT))

    def bloque_vocab(b):
        chips = []
        for w in b["palabras"]:
            sig = curso.significado(w) or ""
            chips.append(ft.Container(ft.Column([glifos(w, size=24), ft.Text(w, size=13, weight=ft.FontWeight.BOLD),
                                                 ft.Text(sig, size=11, color=ft.Colors.OUTLINE)], spacing=1,
                                                horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                                      padding=8, border_radius=8, width=120, border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT)))
        return ft.Column([ft.Text(t("Vocabulario de esta parte"), size=12, color=ft.Colors.OUTLINE),
                          ft.Row(chips, wrap=True, spacing=8, run_spacing=8)], spacing=4)

    def celda(texto, es_glifo):
        crudo = bl.limpiar_celda(texto)
        if "[[" in texto:
            num = crudo.replace("[", "").replace("]", "")
            return ft.Row([glifos(num, size=22), ft.Text(num, size=12, color=ft.Colors.OUTLINE)], spacing=6, tight=True)
        if es_glifo and crudo:
            return glifos(crudo, size=22)
        return ft.Text(crudo, size=13)

    def bloque_tabla(b):
        glifo_col = [("glifo" in h.lower()) for h in b["cab"]]
        cols = [ft.DataColumn(ft.Text(bl.limpiar_celda(h), size=12, weight=ft.FontWeight.BOLD)) for h in b["cab"]]
        filas = [ft.DataRow([ft.DataCell(celda(x, glifo_col[j] if j < len(glifo_col) else False))
                             for j, x in enumerate(f + [""] * (len(cols) - len(f)))]) for f in b["filas"]]
        return ft.Row([ft.DataTable(columns=cols, rows=filas, heading_row_height=36, data_row_min_height=36,
                                    data_row_max_height=56, column_spacing=24)], scroll=ft.ScrollMode.AUTO)

    def md(texto):
        return ft.Markdown(texto, selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                           on_tap_link=lambda e: st.page.launch_url(e.data))

    def dibujar(b):
        if b["t"] == "md":
            return md(b["texto"])
        if b["t"] == "titulo":
            return ft.Text(b["texto"], theme_style=ft.TextThemeStyle.TITLE_MEDIUM)
        if b["t"] == "owee":
            return bloque_owee(b)
        if b["t"] == "vocab":
            return bloque_vocab(b)
        if b["t"] == "tabla":
            return bloque_tabla(b)
        return ft.ExpansionTile(title=ft.Text(t("Ejercicios y respuestas")), controls=[
            ft.Container(md(b["md"]), padding=ft.padding.only(left=16, right=16, bottom=12))])

    # ---------- pantallas ----------
    def selector_modo():
        return ft.Dropdown(label=t("Mostrar"), value=est["modo"], width=260, on_change=cambiar_modo,
                           options=[ft.dropdown.Option(k, t(v)) for k, v in MODOS.items()])

    def mostrar_indice():
        est["lec"] = None
        p = plan()
        filas = []
        for n in curso.NIVELES:
            items = []
            for l in n["lecciones"]:
                hecha = p and curso.estado_leccion(c, p, l["id"]) == "completado"
                items.append(ft.ListTile(
                    dense=True, title=ft.Text(t("Lección {id} — {titulo}", id=l["id"], titulo=l["titulo"]), size=14),
                    leading=ft.Icon(ft.Icons.CHECK_CIRCLE if hecha else ft.Icons.RADIO_BUTTON_UNCHECKED, size=20,
                                    color=ft.Colors.GREEN_400 if hecha else None),
                    on_click=lambda _, i=l["id"]: mostrar_leccion(i)))
            filas.append(ft.ExpansionTile(title=ft.Text(t("Nivel {n} — {titulo}", n=n["n"], titulo=n["titulo"])),
                                          subtitle=ft.Text(n["objetivo"], size=12), controls=items,
                                          initially_expanded=n["n"] == 0))
        estado = []
        if p:
            estado = [ft.Text(t("Tu progreso en el curso: {p:.0%}", p=repo.progreso(c, p))),
                      ft.ProgressBar(value=repo.progreso(c, p))]
        else:
            estado = [ft.ElevatedButton(t("Añadir el curso a mi plan de estudio"), icon=ft.Icons.SCHOOL,
                                        on_click=lambda _: (asegurar_plan(), mostrar_indice()))]
        cuerpo.controls = [
            ft.Text(t("Aprende Owee"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
            ft.Text(t("Owee es un idioma construido: 4 vocales, 14 consonantes, sin géneros ni conjugaciones y con su propia "
                      "escritura en línea (cada sílaba es una consonante con su vocal a la derecha). Aquí tienes su curso por niveles, con tarjetas de glifos y vocabulario. "
                      "Las lecciones están escritas en español."), size=13),
            *estado, selector_modo(), *filas,
            ft.Text(t("Curso y contenido de Owee: Hector Martinez, CC BY-SA 4.0 · oweeme.github.io/owee"), size=11,
                    color=ft.Colors.OUTLINE)]
        st.page.update()

    def mostrar_leccion(id_):
        est["lec"] = id_
        l = curso.leccion(id_)
        todas = [x["id"] for x in curso.lecciones()]
        k = todas.index(id_)
        p = plan()
        hecha = bool(p) and curso.estado_leccion(c, p, id_) == "completado"
        n_tj = len(curso.tarjetas_de_leccion(id_))

        def marcar(e):
            pid = asegurar_plan()
            curso.marcar_leccion(c, pid, id_, e.control.value)

        def crear_tarjetas(_):
            pid = asegurar_plan()
            n = curso.crear_tarjetas_leccion(c, pid, id_)
            st.toast(tn(n, "{n} tarjeta nueva creada. Repásala en «Repaso».", "{n} tarjetas nuevas creadas. Repásalas en «Repaso».")
                     if n else t("Ya tienes todas las tarjetas de esta lección."))

        def ir(i):
            return lambda _: mostrar_leccion(todas[i])

        navegacion = ft.Row([
            ft.OutlinedButton(t("Anterior"), icon=ft.Icons.NAVIGATE_BEFORE, on_click=ir(k - 1), disabled=k == 0),
            ft.OutlinedButton(t("Siguiente"), icon=ft.Icons.NAVIGATE_NEXT, on_click=ir(k + 1), disabled=k == len(todas) - 1)],
            wrap=True)
        acciones = [ft.Switch(label=t("Marcar como hecha"), value=hecha, on_change=marcar)]
        if n_tj:
            acciones.append(ft.ElevatedButton(t("＋ Crear tarjetas de esta lección ({n})", n=n_tj), icon=ft.Icons.STYLE,
                                              on_click=crear_tarjetas))
        cuerpo.controls = [
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip=t("Volver al curso"), on_click=lambda _: mostrar_indice()),
                    ft.Text(t("Lección {id} — {titulo}", id=l["id"], titulo=l["titulo"]),
                            theme_style=ft.TextThemeStyle.TITLE_MEDIUM, expand=True)]),
            selector_modo(), *[dibujar(b) for b in bl.parsear(l["md"])],
            ft.Divider(), ft.Row(acciones, wrap=True), navegacion]
        st.page.update()

    mostrar_indice()
    return cuerpo
