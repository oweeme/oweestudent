import flet as ft

from database import repo
from engine import biblio
from i18n import marcar, t, tn
from ui.components.widgets import confirmar, dialogo

ESTADOS = {"por_leer": marcar("Por leer"), "leyendo": marcar("Leyendo"), "leido": marcar("Leída")}
ICONOS = {"por_leer": ft.Icons.BOOKMARK_BORDER, "leyendo": ft.Icons.AUTO_STORIES, "leido": ft.Icons.CHECK_CIRCLE}
PRIORIDADES = {1: marcar("Alta"), 2: marcar("Media"), 3: marcar("Baja")}
FICHA = (("pregunta", marcar("Pregunta de investigación")), ("metodo", marcar("Método")), ("hallazgos", marcar("Hallazgos")),
         ("limitaciones", marcar("Limitaciones")), ("utilidad", marcar("Cómo me sirve")), ("cita_clave", marcar("Cita clave")),
         ("notas", marcar("Notas")))
SIGUIENTE = {"por_leer": "leyendo", "leyendo": "leido", "leido": "por_leer"}


def _entero(texto):
    try:
        return int(str(texto).strip())
    except ValueError:
        return None


def build(st, recargar, abrir_material=lambda mid, pag: None):
    c = st.conn
    if not st.plan_id:
        return ft.Text(t("Primero crea o elige una asignatura en «Planes»."))
    plan = c.execute("SELECT titulo FROM planes WHERE id=?", (st.plan_id,)).fetchone()
    cuerpo = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    est = {"estado": "todas", "etiqueta": "todas", "texto": ""}
    aviso = ft.Text("")

    def msg(texto, error=False):
        aviso.value, aviso.color = texto, ft.Colors.RED_300 if error else ft.Colors.GREEN_300
        st.page.update()

    # ---------- acciones sobre la colección ----------
    def anadir(_):
        campos = [ft.TextField(label=t("Título")), ft.TextField(label=t("Autores (Apellido, Nombre; Apellido, Nombre)")),
                  ft.TextField(label=t("Año"), width=120), ft.TextField(label=t("Revista, libro o editorial")),
                  ft.TextField(label=t("DOI o enlace")), ft.TextField(label=t("Etiquetas (separadas por comas)"))]

        def ok(v):
            if not v[0].strip():
                return
            doi = v[4].strip()
            repo.agregar_lectura(c, st.plan_id, v[0], autores=v[1].strip(), anio=_entero(v[2]), fuente=v[3].strip(),
                                 doi=doi if not doi.startswith("http") else "", url=doi if doi.startswith("http") else "",
                                 etiquetas=v[5].strip())
            mostrar_lista()
        dialogo(st.page, t("Añadir lectura"), campos, ok)

    def importar(_):
        campo = ft.TextField(label=t("Pega aquí tu BibTeX (de Zotero, Mendeley, Google Scholar…)"), multiline=True,
                             min_lines=8, max_lines=14)

        def ok(v):
            nuevas, repetidas = repo.importar_bibtex(c, st.plan_id, v[0])
            if not (nuevas or repetidas):
                msg(t("No encontré referencias en ese texto."), True)
            else:
                msg(tn(nuevas, "{n} lectura nueva importada.", "{n} lecturas nuevas importadas.") +
                    (" " + tn(repetidas, "{n} ya estaba.", "{n} ya estaban.") if repetidas else ""))
            mostrar_lista()
        dialogo(st.page, t("Importar BibTeX"), [campo], ok, t("Importar"))

    def copiar_bibtex(_):
        filas = repo.lecturas(c, st.plan_id)
        if not filas:
            return msg(t("Aún no hay lecturas."), True)
        st.page.set_clipboard(biblio.a_bibtex(filas))
        msg(t("BibTeX copiado: pégalo en tu gestor de referencias o en tu documento."))

    def etiquetas_ficha():
        return {k: t(v) for k, v in FICHA}

    def copiar_fichas(_):
        filas = [f for f in repo.lecturas(c, st.plan_id) if any((f[k] or "").strip() for k, _ in FICHA)]
        if not filas:
            return msg(t("Aún no hay fichas con contenido."), True)
        st.page.set_clipboard(biblio.fichas_markdown(filas, etiquetas_ficha()))
        msg(t("Fichas copiadas en formato Markdown."))

    # ---------- lista ----------
    def refiltrar(e=None):
        est["estado"], est["etiqueta"], est["texto"] = f_estado.value, f_etiqueta.value, f_texto.value
        mostrar_lista()

    f_estado = ft.Dropdown(label=t("Estado"), width=170, on_change=refiltrar, value="todas",
                           options=[ft.dropdown.Option("todas", t("Todas"))] + [ft.dropdown.Option(k, t(v)) for k, v in ESTADOS.items()])
    f_etiqueta = ft.Dropdown(label=t("Etiqueta"), width=190, on_change=refiltrar, value="todas")
    f_texto = ft.TextField(label=t("Buscar"), width=220, on_submit=refiltrar, icon=ft.Icons.SEARCH)

    def cambiar_estado(lid, estado):
        repo.editar_lectura(c, lid, estado=estado)
        mostrar_lista()

    def fila(f):
        autores = biblio.citar({"titulo": "", "autores": f["autores"], "anio": f["anio"]}).rstrip(". ").strip()
        sub = " · ".join(x for x in (autores, f["fuente"] or "", ", ".join(repo.etiquetas_de(f))) if x)
        return ft.ListTile(
            leading=ft.IconButton(ICONOS[f["estado"]], tooltip=t("Cambiar estado: {estado}", estado=t(ESTADOS[f["estado"]])),
                                  icon_color=ft.Colors.GREEN_400 if f["estado"] == "leido" else None,
                                  on_click=lambda _, i=f["id"], e=SIGUIENTE[f["estado"]]: cambiar_estado(i, e)),
            title=ft.Text(f["titulo"], size=14, weight=ft.FontWeight.W_500), subtitle=ft.Text(sub, size=12) if sub else None,
            on_click=lambda _, i=f["id"]: mostrar_ficha(i))

    def mostrar_lista():
        st.abrir_lectura = None
        r = repo.resumen_lecturas(c, st.plan_id)
        etiquetas = repo.todas_las_etiquetas(c, st.plan_id)
        f_etiqueta.options = [ft.dropdown.Option("todas", t("Todas"))] + [ft.dropdown.Option(e) for e in etiquetas]
        f_etiqueta.visible = bool(etiquetas)
        if est["etiqueta"] not in ["todas"] + etiquetas:
            est["etiqueta"] = f_etiqueta.value = "todas"
        filas = repo.lecturas(c, st.plan_id, None if est["estado"] == "todas" else est["estado"],
                              None if est["etiqueta"] == "todas" else est["etiqueta"], est["texto"])
        cuerpo.controls = [
            ft.Text(t("Lecturas · {plan}", plan=plan["titulo"]), theme_style=ft.TextThemeStyle.HEADLINE_SMALL), aviso,
            ft.Text(t("{a} por leer · {b} leyendo · {c} leídas · {d} esta semana", a=r["por_leer"], b=r["leyendo"],
                      c=r["leido"], d=r["semana"]), size=13),
            ft.Text(t("Tu cola de lectura: guarda cada texto, léelo y rellena su ficha (pregunta, método, hallazgos, "
                      "limitaciones). Las fichas se pueden convertir en tarjetas, exportar y consultar en «Preguntar»."), size=12),
            ft.Row([ft.ElevatedButton(t("＋ Añadir lectura"), on_click=anadir),
                    ft.OutlinedButton(t("Importar BibTeX"), icon=ft.Icons.UPLOAD, on_click=importar),
                    ft.OutlinedButton(t("Copiar BibTeX"), icon=ft.Icons.COPY, on_click=copiar_bibtex),
                    ft.OutlinedButton(t("Copiar fichas (Markdown)"), icon=ft.Icons.NOTES, on_click=copiar_fichas)], wrap=True),
            ft.Row([f_estado, f_etiqueta, f_texto], wrap=True),
            *(([fila(f) for f in filas]) or [ft.Text(t("Aún no hay lecturas aquí."))])]
        st.page.update()

    # ---------- ficha ----------
    def mostrar_ficha(lid):
        l = repo.lectura(c, lid)
        if l is None:
            return mostrar_lista()
        campos = {
            "titulo": ft.TextField(label=t("Título"), value=l["titulo"]),
            "autores": ft.TextField(label=t("Autores (Apellido, Nombre; Apellido, Nombre)"), value=l["autores"] or ""),
            "anio": ft.TextField(label=t("Año"), value=str(l["anio"] or ""), width=120),
            "fuente": ft.TextField(label=t("Revista, libro o editorial"), value=l["fuente"] or "", expand=True),
            "doi": ft.TextField(label=t("DOI"), value=l["doi"] or "", width=260),
            "url": ft.TextField(label=t("Enlace"), value=l["url"] or "", expand=True),
            "etiquetas": ft.TextField(label=t("Etiquetas (separadas por comas)"), value=l["etiquetas"] or "")}
        estado = ft.Dropdown(label=t("Estado"), value=l["estado"], width=170,
                             options=[ft.dropdown.Option(k, t(v)) for k, v in ESTADOS.items()])
        prio = ft.Dropdown(label=t("Prioridad"), value=str(l["prioridad"] or 2), width=150,
                           options=[ft.dropdown.Option(str(k), t(v)) for k, v in PRIORIDADES.items()])
        mats = repo.materiales(c, st.plan_id)
        mat = ft.Dropdown(label=t("Archivo adjunto de esta lectura"), value=str(l["material_id"] or "ninguno"), width=320,
                          options=[ft.dropdown.Option("ninguno", t("(ninguno)"))] + [ft.dropdown.Option(str(m["id"]), m["titulo"]) for m in mats])
        ficha = {k: ft.TextField(label=t(v), value=l[k] or "", multiline=True, min_lines=2, max_lines=8) for k, v in FICHA}

        def guardar(_):
            if not campos["titulo"].value.strip():
                return msg(t("El título no puede estar vacío."), True)
            datos = {k: campos[k].value.strip() for k in ("titulo", "autores", "fuente", "doi", "url", "etiquetas")}
            datos["anio"] = _entero(campos["anio"].value)
            datos.update({k: f.value.strip() for k, f in ficha.items()})
            datos["estado"], datos["prioridad"] = estado.value, int(prio.value)
            datos["material_id"] = None if mat.value in (None, "ninguno") else int(mat.value)
            repo.editar_lectura(c, lid, **datos)
            msg(t("Ficha guardada"))

        def tarjetas(_):
            guardar(None)
            plantillas = {"pregunta": t("{cita}: ¿cuál era la pregunta de investigación?"), "metodo": t("{cita}: ¿qué método usó?"),
                          "hallazgos": t("{cita}: ¿qué encontró?"), "limitaciones": t("{cita}: ¿qué limitaciones tiene?"),
                          "utilidad": t("{cita}: ¿cómo me sirve para mi trabajo?")}
            n = repo.tarjetas_de_lectura(c, lid, plantillas)
            msg(tn(n, "{n} tarjeta creada desde la ficha. Repásala en «Repaso».", "{n} tarjetas creadas desde la ficha. Repásalas en «Repaso».")
                if n else t("No hay campos nuevos de la ficha para convertir en tarjetas."), n == 0)

        def borrar(_):
            confirmar(st.page, t("¿Borrar esta lectura y su ficha?"), lambda: (repo.borrar_lectura(c, lid), mostrar_lista()))

        acciones = [ft.ElevatedButton(t("Guardar"), icon=ft.Icons.SAVE, on_click=guardar),
                    ft.OutlinedButton(t("Crear tarjetas de la ficha"), icon=ft.Icons.STYLE, on_click=tarjetas)]
        if l["material_id"]:
            acciones.append(ft.OutlinedButton(t("Abrir el archivo"), icon=ft.Icons.MENU_BOOK,
                                              on_click=lambda _: abrir_material(l["material_id"], 1)))
        acciones.append(ft.TextButton(t("Borrar lectura"), icon=ft.Icons.DELETE_OUTLINE, on_click=borrar))
        cuerpo.controls = [
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip=t("Volver a las lecturas"), on_click=lambda _: mostrar_lista()),
                    ft.Text(biblio.citar(l), theme_style=ft.TextThemeStyle.TITLE_MEDIUM, expand=True)]), aviso,
            campos["titulo"], campos["autores"], ft.Row([campos["anio"], campos["fuente"]], wrap=True),
            ft.Row([campos["doi"], campos["url"]], wrap=True), campos["etiquetas"],
            ft.Row([estado, prio, mat], wrap=True), ft.Divider(),
            ft.Text(t("Ficha de lectura"), weight=ft.FontWeight.BOLD), *ficha.values(), ft.Row(acciones, wrap=True)]
        st.page.update()

    if st.abrir_lectura:       # llegamos desde una cita
        lid, st.abrir_lectura = st.abrir_lectura, None
        mostrar_ficha(lid)
    else:
        mostrar_lista()
    return cuerpo
