import os
import threading
from pathlib import Path

import flet as ft

from database import repo
from engine import ai, material as mat, tarjetas as tj
from ui.components.widgets import confirmar, dialogo

EXT = ["pdf", "docx", "xlsx", "csv", "txt", "md"]
ICONOS = {"pdf": ft.Icons.PICTURE_AS_PDF, "docx": ft.Icons.DESCRIPTION, "xlsx": ft.Icons.TABLE_CHART,
          "csv": ft.Icons.TABLE_CHART, "txt": ft.Icons.ARTICLE, "md": ft.Icons.ARTICLE}


def build(st, recargar):
    if not st.plan_id:
        return ft.Text("Primero crea o elige una asignatura en «Planes».")
    c = st.conn
    plan = c.execute("SELECT titulo FROM planes WHERE id=?", (st.plan_id,)).fetchone()
    cuerpo = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
    est = {"mid": None, "pag": 1, "reenlazar": None}
    aviso = ft.Text("")

    def msg(t, error=False):
        aviso.value, aviso.color = t, ft.Colors.RED_300 if error else ft.Colors.GREEN_300
        st.page.update()

    # ---------- adjuntar ----------
    picker = ft.FilePicker()
    st.page.overlay.append(picker)
    ruta = ft.TextField(label="…o pega la ruta del archivo", width=320)
    solo_enlazar = ft.Switch(label="Solo enlazar (no copiar el archivo)", value=False)

    def adjuntar(path):
        path = path.strip().strip("'\"")
        try:
            if est["reenlazar"]:          # volver a vincular un archivo que venía de otro equipo
                m = c.execute("SELECT * FROM materiales WHERE id=?", (est["reenlazar"],)).fetchone()
                est["reenlazar"] = None
                if mat.hash_archivo(path) != m["hash"]:
                    msg("Ese archivo no es el mismo (su contenido es distinto).", True)
                    return
                repo.vincular_archivo(c, m["id"], mat.copiar_a_app(path, m["hash"]))
                msg("Archivo vinculado ✅")
                return mostrar_lista()
            h = mat.hash_archivo(path)
            ya = repo.material_por_hash(c, h, st.plan_id)
            if ya:
                msg(f"«{ya['titulo']}» ya estaba adjuntado en esta asignatura: no se duplicó.")
                return mostrar_lista()
            otro = repo.material_por_hash(c, h)
            destino = path if solo_enlazar.value else mat.copiar_a_app(path, h)
            nombre = Path(path).name
            repo.agregar_material(c, st.plan_id, Path(path).stem, mat.tipo_de(path), h, nombre, destino, os.path.getsize(path))
            msg("Adjuntado ✅" + (" (ya lo tenías en otra asignatura: se reutilizó el mismo archivo)" if otro and not solo_enlazar.value else ""))
            mostrar_lista()
        except Exception as ex:
            msg(f"No se pudo adjuntar: {ex}", True)

    picker.on_result = lambda e: adjuntar(e.files[0].path) if e.files else None

    # ---------- lista ----------
    def disponible(m):
        return bool(m["ruta"]) and os.path.exists(m["ruta"])

    def abrir(mid):
        aviso.value = ""
        est["mid"] = mid
        est["pag"] = c.execute("SELECT pagina_actual FROM materiales WHERE id=?", (mid,)).fetchone()[0] or 1
        mostrar_lector()

    def pedir_archivo(mid):
        est["reenlazar"] = mid
        picker.pick_files(allowed_extensions=EXT)

    def quitar(m):
        confirmar(st.page, f"¿Quitar «{m['titulo']}» y sus notas? (el archivo original no se borra)",
                  lambda: (repo.borrar_material(c, m["id"]), mostrar_lista()))

    def mostrar_lista():
        est["mid"] = None
        filas = []
        for m in repo.materiales(c, st.plan_id):
            n_notas = len(repo.notas_material(c, m["id"]))
            ok = disponible(m)
            sub = f"{m['tipo']} · " + (f"página {m['pagina_actual']}/{m['paginas']}" if m["paginas"] else "sin empezar") + \
                  f" · {n_notas} notas" + ("" if ok else "  ·  ⚠ el archivo no está en este equipo")
            filas.append(ft.ListTile(
                leading=ft.Icon(ICONOS.get(m["tipo"], ft.Icons.INSERT_DRIVE_FILE)), title=ft.Text(m["titulo"]),
                subtitle=ft.Text(sub, size=12),
                on_click=(lambda _, i=m["id"]: abrir(i)) if ok else (lambda _, i=m["id"]: pedir_archivo(i)),
                trailing=ft.PopupMenuButton(items=[
                    ft.PopupMenuItem(text="Leer" if ok else "Vincular el archivo aquí",
                                     on_click=(lambda _, i=m["id"]: abrir(i)) if ok else (lambda _, i=m["id"]: pedir_archivo(i))),
                    ft.PopupMenuItem(text="Quitar", on_click=lambda _, m=m: quitar(m))])))
        cuerpo.controls = [
            ft.Text(f"Material · {plan['titulo']}", style=ft.TextThemeStyle.HEADLINE_SMALL), aviso,
            ft.Text("Adjunta tus libros, PDFs, Word, Excel o CSV. Un mismo archivo nunca se duplica, aunque lo "
                    "adjuntes en varias asignaturas. Lee dentro de la app, guarda conclusiones y crea tarjetas.", size=13),
            ft.ElevatedButton("＋ Adjuntar archivo", icon=ft.Icons.ATTACH_FILE,
                              on_click=lambda _: picker.pick_files(allowed_extensions=EXT)),
            ft.Row([ruta, ft.OutlinedButton("Adjuntar", on_click=lambda _: adjuntar(ruta.value))], wrap=True),
            solo_enlazar,
            *(filas or [ft.Text("Aún no hay material en esta asignatura.")]),
        ]
        st.page.update()

    # ---------- lector ----------
    def mostrar_lector():
        m = c.execute("SELECT * FROM materiales WHERE id=?", (est["mid"],)).fetchone()
        try:
            total = mat.num_paginas(m["ruta"])
            est["pag"] = max(1, min(est["pag"], total))
            texto = mat.leer_pagina(m["ruta"], est["pag"])
        except Exception as ex:
            msg(f"No se pudo leer el archivo: {ex}", True)
            return mostrar_lista()
        repo.progreso_lectura(c, m["id"], est["pag"], total)
        pag_campo = ft.TextField(value=str(est["pag"]), width=80, text_align=ft.TextAlign.CENTER,
                                 keyboard_type=ft.KeyboardType.NUMBER, dense=True)

        def ir(n):
            try:
                est["pag"] = int(n)
            except ValueError:
                return
            mostrar_lector()

        pag_campo.on_submit = lambda e: ir(pag_campo.value)
        nota = ft.TextField(label=f"Tu conclusión o idea clave (página {est['pag']})", multiline=True, min_lines=2, max_lines=6)
        tipo_nota = ft.Dropdown(label="Tipo", value="conclusion", width=180, options=[
            ft.dropdown.Option("conclusion", "Conclusión"), ft.dropdown.Option("cita", "Cita"),
            ft.dropdown.Option("duda", "Duda"), ft.dropdown.Option("idea", "Idea")])
        salida_ia = ft.Text("", selectable=True)

        def guardar_nota(_):
            if nota.value.strip():
                repo.agregar_nota_material(c, m["id"], est["pag"], nota.value, tipo_nota.value)
                mostrar_lector()

        def tema_destino():
            return m["tema_id"] or repo.tema_para_tarjetas(c, st.plan_id)

        def tarjetas_offline(_):
            base = texto + "\n" + "\n".join(n["texto"] for n in repo.notas_material(c, m["id"], est["pag"]))
            n = repo.crear_tarjetas(c, tema_destino(), tj.desde_apuntes(base), "material")
            msg(f"{n} tarjetas creadas desde esta página." if n else
                "No encontré definiciones («Término: explicación») ni **negritas**. Guarda tus conclusiones y vuelve a probar, "
                "o crea tarjetas a mano en «Estudiar».", n == 0)

        def hilo(fn):
            if not ai.ia_disponible():
                return msg("Configura la IA en Ajustes para usar esto.", True)
            salida_ia.value = "Pensando…"
            st.page.update()

            def hacer():
                try:
                    fn()
                except Exception as ex:
                    salida_ia.value = f"Error IA: {ex}"
                st.page.update()
            threading.Thread(target=hacer, daemon=True).start()

        def resumir(_):
            def f():
                salida_ia.value = ai.resumir_pagina(texto) + "\n\n(Resumen automático: verifícalo con el texto.)"
            hilo(f)

        def tarjetas_ia(_):
            def f():
                n = repo.crear_tarjetas(c, tema_destino(), ai.tarjetas_desde_material(m["titulo"], texto), "ia")
                salida_ia.value = f"{n} tarjetas creadas con IA. Revísalas: un modelo pequeño puede fallar."
            hilo(f)

        notas = [ft.ListTile(dense=True, title=ft.Text(n["texto"], size=13), subtitle=ft.Text(n["tipo"], size=11),
                             trailing=ft.IconButton(ft.Icons.CLOSE, icon_size=16,
                                                    on_click=lambda _, i=n["id"]: (repo.borrar_nota_material(c, i), mostrar_lector())))
                 for n in repo.notas_material(c, m["id"], est["pag"])]
        todas = len(repo.notas_material(c, m["id"]))
        extra = []
        if m["tipo"] in ("xlsx", "csv"):
            extra = [ft.OutlinedButton("Importar como tarjetas de vocabulario…", icon=ft.Icons.TRANSLATE,
                                       on_click=lambda _: dialogo_vocabulario(m))]
        cuerpo.controls = [
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip="Volver al material", on_click=lambda _: mostrar_lista()),
                    ft.Text(m["titulo"], style=ft.TextThemeStyle.TITLE_MEDIUM, expand=True)]), aviso,
            ft.Row([ft.IconButton(ft.Icons.NAVIGATE_BEFORE, on_click=lambda _: ir(est["pag"] - 1), disabled=est["pag"] <= 1),
                    pag_campo, ft.Text(f"de {total}"),
                    ft.IconButton(ft.Icons.NAVIGATE_NEXT, on_click=lambda _: ir(est["pag"] + 1), disabled=est["pag"] >= total),
                    ft.Text(f"{todas} notas en total", size=12)], wrap=True),
            ft.Row([ft.Container(ft.Text(texto, selectable=True, size=15), padding=12, expand=True,
                                 border=ft.border.all(1, ft.Colors.OUTLINE), border_radius=8)]),
            ft.Text("Tus conclusiones de esta página", weight=ft.FontWeight.BOLD), *notas,
            nota, ft.Row([tipo_nota, ft.ElevatedButton("Guardar", icon=ft.Icons.SAVE, on_click=guardar_nota)], wrap=True),
            ft.Row([ft.OutlinedButton("Crear tarjetas de esta página", icon=ft.Icons.STYLE, on_click=tarjetas_offline),
                    ft.OutlinedButton("✨ Con IA", on_click=tarjetas_ia),
                    ft.OutlinedButton("✨ Resumir", on_click=resumir)], wrap=True),
            *extra, salida_ia,
        ]
        st.page.update()

    # ---------- vocabulario desde Excel / CSV ----------
    def dialogo_vocabulario(m):
        try:
            hojas, filas = mat.leer_tabla(m["ruta"], 0)
        except Exception as ex:
            return msg(f"No se pudo leer la tabla: {ex}", True)
        ncol = max((len(f) for f in filas[:50]), default=2)
        cab = filas[0] if filas else []
        nombres = [f"{i + 1}: {cab[i] if i < len(cab) and cab[i] else 'columna ' + str(i + 1)}" for i in range(ncol)]
        op = lambda: [ft.dropdown.Option(str(i), nombres[i]) for i in range(ncol)]
        hoja = ft.Dropdown(label="Hoja", value="0", options=[ft.dropdown.Option(str(i), h) for i, h in enumerate(hojas)])
        frente = ft.Dropdown(label="Pregunta (ej. palabra en alemán/chino)", value="0", options=op())
        reverso = ft.Dropdown(label="Respuesta (ej. significado)", value="1" if ncol > 1 else "0", options=op())
        extra = ft.Dropdown(label="Dato extra opcional (ej. pinyin)", value="ninguno",
                            options=[ft.dropdown.Option("ninguno", "(ninguno)")] + op())
        cabecera = ft.Switch(label="La primera fila es cabecera", value=True)
        ambos = ft.Switch(label="Crear también respuesta → pregunta", value=False)

        def ok(_v):
            try:
                _, filas_h = mat.leer_tabla(m["ruta"], int(hoja.value or 0))
                pares = mat.a_tarjetas(filas_h, int(frente.value), int(reverso.value),
                                       None if extra.value in (None, "ninguno") else int(extra.value),
                                       cabecera.value, ambos.value)
                n = repo.crear_tarjetas(c, m["tema_id"] or repo.tema_para_tarjetas(c, st.plan_id), pares, "excel")
                msg(f"{n} tarjetas creadas (las repetidas se omitieron). Repásalas en «Repaso».")
            except Exception as ex:
                msg(f"No se pudo importar: {ex}", True)
        dialogo(st.page, "Importar vocabulario", [hoja, frente, reverso, extra, cabecera, ambos], ok, "Crear tarjetas")

    mostrar_lista()
    return cuerpo
