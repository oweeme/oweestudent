from datetime import date

import flet as ft

from database import repo
from engine import anki
from i18n import marcar, t, tn
from ui.components import guardar

ALCANCES = {"todo": marcar("Todo mi estudio"), "plan": marcar("Esta asignatura"), "tema": marcar("Un tema")}
FORMATOS = {"apkg": marcar("Paquete de Anki (.apkg)"), "csv": marcar("Texto CSV para importar en Anki")}


def _nombre(texto: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in texto).strip("-")[:40] or "tarjetas"


def build(st):
    c = st.conn
    aviso = ft.Text("", selectable=True)
    temas = [(tm["id"], tm["titulo"]) for u in (repo.unidades(c, st.plan_id) if st.plan_id else []) for tm in repo.temas(c, u["id"])]
    alcance = ft.Dropdown(label=t("Qué exportar"), width=260, value="plan" if st.plan_id else "todo", on_change=lambda e: refrescar(),
                          options=[ft.dropdown.Option(k, t(v)) for k, v in ALCANCES.items() if k == "todo" or st.plan_id])
    tema = ft.Dropdown(label=t("Tema"), width=320, visible=False, value=str(temas[0][0]) if temas else None, on_change=lambda e: refrescar(),
                       options=[ft.dropdown.Option(str(i), x) for i, x in temas])
    formato = ft.Dropdown(label=t("Formato"), width=320, value="apkg", on_change=lambda e: refrescar(),
                          options=[ft.dropdown.Option(k, t(v)) for k, v in FORMATOS.items()])
    progreso = ft.Switch(label=t("Conservar mi progreso de repaso"), value=True)
    cuenta = ft.Text("", weight=ft.FontWeight.BOLD)
    explicacion = ft.Text("", size=12)

    def seleccion():
        return anki.tarjetas_a_exportar(c, st.perfil_id, st.plan_id if alcance.value in ("plan", "tema") else None,
                                        int(tema.value) if alcance.value == "tema" and tema.value else None)

    def refrescar():
        tema.visible = alcance.value == "tema"
        progreso.visible = formato.value == "apkg"
        n = len(seleccion())
        cuenta.value = tn(n, "{n} tarjeta para exportar", "{n} tarjetas para exportar")
        explicacion.value = (t("En Anki: Archivo → Importar y elige el archivo. Para conservar tu progreso marca «Incluir información de programación». "
                               "Si exportas otra vez, Anki actualiza las tarjetas en vez de duplicarlas.") if formato.value == "apkg" else
                             t("En Anki: Archivo → Importar, elige el archivo y asigna las columnas: frente, reverso y etiquetas."))
        st.page.update()

    def terminado(destino, error):
        if error:
            aviso.value, aviso.color = t("No se pudo exportar: {ex}", ex=error), ft.Colors.RED_300
        else:
            aviso.value, aviso.color = t("✅ Exportado en: {ruta}", ruta=str(destino)), ft.Colors.GREEN_400
        st.page.update()

    estado = {"filas": []}

    def escribir(destino):
        if formato.value == "apkg":
            anki.crear_apkg(estado["filas"], destino, progreso.value)
        else:
            destino.write_text(anki.a_csv(estado["filas"]), encoding="utf-8")

    picker = guardar.preparar(st.page, lambda ruta: guardar.escribir_elegido(ruta, "apkg" if formato.value == "apkg" else "tsv", escribir, terminado))

    def exportar(_):
        filas = estado["filas"] = seleccion()
        if not filas:
            aviso.value, aviso.color = t("No hay tarjetas que exportar."), ft.Colors.RED_300
            return st.page.update()
        base = f"OweeStudent-{date.today():%Y%m%d}-{_nombre(filas[0]['plan'] if alcance.value != 'todo' else 'todo')}"
        guardar.guardar(st.page, picker, base, "apkg" if formato.value == "apkg" else "tsv", escribir, terminado)

    refrescar()
    return ft.Column([
        ft.Text(t("Exportar a Anki"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
        ft.Text(t("Lleva tus tarjetas a Anki (escritorio, AnkiDroid o AnkiMobile). Tus datos siguen siendo tuyos y se quedan en tu equipo."), size=13),
        ft.Row([alcance, tema], wrap=True), formato, progreso, cuenta, explicacion,
        ft.ElevatedButton(t("Exportar"), icon=ft.Icons.DOWNLOAD, on_click=exportar), aviso,
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
