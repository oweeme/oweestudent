import flet as ft

from database import repo
from engine import escritura_owee as motor
from i18n import marcar, owee, t
from owee_curso import curso
from ui.components.owee_texto import glifos
from ui.components.teclado_owee import teclado

MODOS_VISTA = {"taller": marcar("Taller libre"), "practica": marcar("Práctica")}


def build(st, recargar=lambda: None):
    """Escribir en Owee Script dentro de la app: un taller libre (teclado de sílabas) y rondas de práctica con las palabras
    del curso. Las palabras que fallas se añaden a «Repaso»."""
    c = st.conn
    est = {"vista": "taller", "ronda": None, "i": 0, "ok": 0, "respondida": False}
    cuerpo = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    escrito: list[str] = []                      # lo compuesto con el teclado, en romano

    def romano() -> str:
        return "".join(escrito)

    def selector():
        def cambiar(e):
            est["vista"] = next(iter(e.control.selected))
            mostrar()
        return ft.SegmentedButton(selected={est["vista"]}, on_change=cambiar, allow_multiple_selection=False,
                                  segments=[ft.Segment(value=k, label=ft.Text(t(v))) for k, v in MODOS_VISTA.items()])

    # ---------- piezas comunes: visor + teclas de control ----------
    visor = glifos("", size=44, selectable=True)
    visor_romano = ft.Text("", size=14, color=ft.Colors.OUTLINE)
    campo = ft.TextField(label=t("O escribe en romano"), dense=True, width=300)

    def refrescar():
        visor.value = owee.a_escritura(romano())
        visor_romano.value = romano()
        if campo.value != romano():
            campo.value = romano()
        st.page.update()

    def poner(texto):
        escrito.append(texto)
        refrescar()

    def desde_campo(e):
        escrito[:] = [campo.value or ""]
        visor.value = owee.a_escritura(campo.value or "")
        visor_romano.value = campo.value or ""
        st.page.update()
    campo.on_change = desde_campo

    def borrar(_):
        if escrito:
            texto = romano()[:-1] if len(escrito) == 1 else None
            if texto is not None:
                escrito[:] = [texto] if texto else []
            else:
                escrito.pop()
        refrescar()

    def limpiar(_):
        escrito.clear()
        refrescar()

    controles = ft.Row([ft.OutlinedButton(t("⌫ Borrar"), on_click=borrar), ft.OutlinedButton(t("Espacio"), on_click=lambda _: poner(" ")),
                        ft.OutlinedButton(t("Nexo (-)"), on_click=lambda _: poner("-")), ft.OutlinedButton(t("Limpiar"), on_click=limpiar)], wrap=True)

    def zona_escritura():
        return ft.Container(ft.Column([ft.Row([visor], scroll=ft.ScrollMode.AUTO), visor_romano], spacing=2), padding=12, border_radius=8,
                            border=ft.border.all(1, ft.Colors.OUTLINE), height=110)

    # ---------- taller libre ----------
    def mostrar_taller():
        escrito.clear()
        refrescar_vacio()

        def copiar(_):
            st.page.set_clipboard(visor.value or "")
            st.toast(t("Copiado en escritura Owee"))
        cuerpo.controls = [
            selector(),
            ft.Text(t("Escribe con el teclado de sílabas (o en romano) y mira tu texto en escritura Owee. Una palabra con mayúscula inicial es un nombre propio."), size=13),
            zona_escritura(), campo, controles,
            ft.OutlinedButton(t("Copiar en escritura Owee"), icon=ft.Icons.COPY, on_click=copiar),
            teclado(poner)]
        st.page.update()

    def refrescar_vacio():
        visor.value, visor_romano.value, campo.value = "", "", ""

    # ---------- práctica ----------
    def mostrar_practica():
        plan_id = curso.plan_del_curso(c, st.perfil_id)
        sig = curso.siguiente_leccion(c, plan_id) if plan_id else None      # palabras hasta la lección que te toca
        pool = motor.palabras(sig["id"] if sig else None) or motor.palabras()
        if not pool:
            cuerpo.controls = [selector(), ft.Text(t("Aún no hay palabras: avanza en el curso."))]
            st.page.update()
            return
        if est["ronda"] is None:
            est.update(ronda=motor.ronda(pool, 5), i=0, ok=0, respondida=False)
        pregunta()

    def nueva_ronda(_=None):
        est["ronda"] = None
        mostrar_practica()

    def pregunta():
        r, i = est["ronda"], est["i"]
        if i >= len(r):
            return resultado()
        q = r[i]
        escrito.clear()
        refrescar_vacio()
        est["respondida"] = False
        veredicto = ft.Text("", size=15, weight=ft.FontWeight.BOLD)
        siguiente = ft.ElevatedButton(t("Siguiente"), visible=False)
        comprobar = ft.ElevatedButton(t("Comprobar"), icon=ft.Icons.CHECK)
        if q["modo"] == "es_a_owee":
            enunciado = ft.Text(t("Escribe en Owee: «{sig}»", sig=q["significado"]), size=18, weight=ft.FontWeight.W_500)
        elif q["modo"] == "glifo_a_owee":
            enunciado = ft.Column([ft.Text(t("Copia esta palabra con el teclado"), size=14), glifos(q["palabra"], size=56)], spacing=2)
        else:
            enunciado = ft.Column([ft.Text(t("Lee y escribe en romano"), size=14), glifos(q["palabra"], size=56)], spacing=2)
        solo_romano = q["modo"] == "glifo_a_romano"

        def comprobar_click(_):
            if est["respondida"]:
                return
            est["respondida"] = True
            ok = motor.comprobar(romano() or campo.value or "", q["palabra"])
            if ok:
                est["ok"] += 1
                veredicto.value, veredicto.color = t("✅ Correcto"), ft.Colors.GREEN_400
            else:
                veredicto.value, veredicto.color = t("❌ Era: {palabra}", palabra=q["palabra"]), ft.Colors.RED_300
                plan_id = curso.plan_del_curso(c, st.perfil_id)
                tema = repo.tema_para_tarjetas(c, plan_id) if plan_id else None
                if tema:       # lo que fallas vuelve en «Repaso»
                    repo.crear_tarjetas(c, tema, [(curso.MARCA_OWEE + q["palabra"], q["significado"])], "owee")
                    repo.crear_tarjetas(c, tema, [(q["significado"], curso.MARCA_OWEE + q["palabra"])], "produccion")
                    est["fallos"] = est.get("fallos", 0) + 1
            comprobar.visible, siguiente.visible = False, True
            st.page.update()

        def avanzar(_):
            est["i"] += 1
            pregunta()
        comprobar.on_click, siguiente.on_click = comprobar_click, avanzar
        cuerpo.controls = [selector(), ft.ProgressBar(value=i / len(r)), ft.Text(t("Palabra {i} de {n}", i=i + 1, n=len(r)), size=12, color=ft.Colors.OUTLINE),
                           enunciado, *([] if solo_romano else [zona_escritura()]), campo, *([] if solo_romano else [controles]),
                           ft.Row([comprobar, siguiente]), veredicto, *([] if solo_romano else [teclado(poner, incluir_digitos=False)])]
        st.page.update()

    def resultado():
        r = est["ronda"]
        extra = [ft.Text(t("Los fallos se añadieron a «Repaso» para que vuelvan."), size=13)] if est.get("fallos") else []
        est["fallos"] = 0
        cuerpo.controls = [selector(), ft.Text(t("Resultado: {ok} de {n}", ok=est["ok"], n=len(r)), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                           *extra, ft.ElevatedButton(t("Nueva ronda"), icon=ft.Icons.REFRESH, on_click=nueva_ronda)]
        st.page.update()

    def mostrar():
        mostrar_taller() if est["vista"] == "taller" else mostrar_practica()

    mostrar()
    return cuerpo
