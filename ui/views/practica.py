import threading
import time

import flet as ft

from database import repo
from engine import ai
from engine import errores
from engine import nivel as niveles
from engine import material as mat
from engine import practica as pr
from i18n import marcar, t, tn
from ui.components.owee_texto import texto_tarjeta

NOMBRES_TIPO = {"recuperacion": marcar("Recuperación libre"), "feynman": marcar("Explícalo (Feynman)"), "simulacro": marcar("Simulacro")}
FUENTES = {"tarjetas": marcar("Mis tarjetas de este tema"), "material": marcar("Una página de un archivo"),
           "lectura": marcar("La ficha de una lectura"), "texto": marcar("Un texto que pego")}
TIPOS_SIMULACRO = {"mixto": marcar("Mixto"), "opciones": marcar("Opción múltiple"), "abierta": marcar("Respuesta abierta")}
ALCANCES = {"tema": marcar("Este tema"), "plan": marcar("Esta asignatura"), "todas": marcar("Todas mis asignaturas"),
            "debiles": marcar("Mis puntos débiles")}


def _lista(titulo, items, color=None):
    if not items:
        return []
    return [ft.Text(titulo, weight=ft.FontWeight.BOLD, size=13, color=color),
            *[ft.Text("• " + x, size=13, selectable=True) for x in items]]


def build(st, ir_a_repaso=lambda: None):
    c = st.conn
    if not st.plan_id:
        return ft.Text(t("Primero crea o elige una asignatura en «Planes»."))
    temas = [(tm["id"], tm["titulo"]) for u in repo.unidades(c, st.plan_id) for tm in repo.temas(c, u["id"])]
    if not temas:
        return ft.Text(t("Esta asignatura aún no tiene temas. Añade alguno en «Plan»."))
    aviso = ft.Text("")
    pref = niveles.ajustes(st.nivel())
    compartido = {"refuerzo": None, "tabs": None}      # el botón de «Puntos débiles» arranca un simulacro de refuerzo

    def msg(texto, error=False):
        aviso.value, aviso.color = texto, ft.Colors.RED_300 if error else ft.Colors.GREEN_300
        st.page.update()

    def selector_tema():
        valor = st.tema_id if st.tema_id in [i for i, _ in temas] else temas[0][0]
        return ft.Dropdown(label=t("Tema"), value=str(valor), width=320, options=[ft.dropdown.Option(str(i), x) for i, x in temas])

    def historial(tipo):
        filas = pr.historial(c, st.plan_id, tipo, 5)
        if not filas:
            return ft.Text(t("Aún no has hecho ninguna práctica de este tipo."), size=12, color=ft.Colors.OUTLINE)
        return ft.Column([ft.Text(t("Tus últimas prácticas"), size=12, color=ft.Colors.OUTLINE),
                          *[ft.Text(f"{f['fecha']} · {round(f['puntaje'] or 0)}%", size=12) for f in filas]], spacing=2)

    # ---------- referencia (con qué comparo lo que recuerdo) ----------
    class Referencia:
        def __init__(self, tema_dd):
            self.tema_dd = tema_dd
            self.fuente = ft.Dropdown(label=t("Compararlo con"), width=300, value="tarjetas", on_change=self.cambiar,
                                      options=[ft.dropdown.Option(k, t(v)) for k, v in FUENTES.items()])
            self.mats = repo.materiales(c, st.plan_id)
            self.mat = ft.Dropdown(label=t("Archivo"), width=300, visible=False, value=str(self.mats[0]["id"]) if self.mats else None,
                                   options=[ft.dropdown.Option(str(m["id"]), m["titulo"]) for m in self.mats])
            self.pag = ft.TextField(label=t("Página"), value="1", width=90, visible=False)
            self.lects = repo.lecturas(c, st.plan_id)
            self.lect = ft.Dropdown(label=t("Lectura"), width=300, visible=False, value=str(self.lects[0]["id"]) if self.lects else None,
                                    options=[ft.dropdown.Option(str(l["id"]), l["titulo"]) for l in self.lects])
            self.texto_pegado = ft.TextField(label=t("Pega aquí el texto de referencia"), multiline=True, min_lines=4, max_lines=8, visible=False)
            self.control = ft.Column([self.fuente, ft.Row([self.mat, self.pag], wrap=True), self.lect, self.texto_pegado], spacing=8)

        def cambiar(self, _=None):
            f = self.fuente.value
            self.mat.visible = self.pag.visible = f == "material"
            self.lect.visible = f == "lectura"
            self.texto_pegado.visible = f == "texto"
            st.page.update()

        def texto(self) -> str:
            f = self.fuente.value
            try:
                if f == "tarjetas":
                    return pr.referencia_de_tema(c, int(self.tema_dd.value))
                if f == "material" and self.mat.value:
                    m = next(x for x in self.mats if str(x["id"]) == self.mat.value)
                    if not m["ruta"]:
                        return ""
                    n = max(1, int(self.pag.value or 1))
                    return mat.leer_pagina(m["ruta"], n)[:3000]
                if f == "lectura" and self.lect.value:
                    return pr.referencia_de_lectura(c, int(self.lect.value))
                if f == "texto":
                    return self.texto_pegado.value.strip()
            except (ValueError, OSError, StopIteration):
                return ""
            return ""

    def autoevaluacion():
        return ft.Slider(min=0, max=5, divisions=5, value=3, label="{value}")

    # ---------- 1 · recuperación libre ----------
    def pestana_recuperacion():
        tema = selector_tema()
        ref = Referencia(tema)
        recuerdo = ft.TextField(label=t("Escribe todo lo que recuerdas del tema, sin mirar nada"), multiline=True, min_lines=8, max_lines=16)
        zona = ft.Column(spacing=8)

        def comparar(_):
            texto_ref = ref.texto()
            if not recuerdo.value.strip():
                return msg(t("Primero escribe lo que recuerdas."), True)
            if not texto_ref.strip():
                return msg(t("No tengo con qué comparar: crea tarjetas de este tema o elige otra referencia."), True)
            aviso.value = ""
            cob = pr.cobertura(texto_ref, recuerdo.value)
            nota = autoevaluacion()
            ia_out = ft.Column(spacing=4)
            usar_ia = ai.ia_disponible()

            def evaluar(_):
                ia_out.controls = [ft.Text(t("La IA está comparando…"), size=12)]
                st.page.update()

                def hacer():
                    try:
                        r = pr.evaluar_recuperacion_ia(texto_ref, recuerdo.value)
                        ia_out.controls = [*_lista(t("Bien"), r["correcto"], ft.Colors.GREEN_400),
                                           *_lista(t("Te faltó"), r["falta"], ft.Colors.AMBER_400),
                                           *_lista(t("Revisa (contradice la referencia)"), r["errores"], ft.Colors.RED_300),
                                           ft.Text(t("Una IA pequeña puede equivocarse: confía más en la referencia que en ella."),
                                                   size=11, color=ft.Colors.OUTLINE)]
                    except Exception as ex:
                        ia_out.controls = [ft.Text(t("Error IA: {ex}", ex=ex), color=ft.Colors.RED_300, size=12)]
                    st.page.update()
                threading.Thread(target=hacer, daemon=True).start()

            def guardar(_):
                tid = int(tema.value)
                prox = repo.guardar_nota(c, tid, recuerdo.value.strip(), int(nota.value))
                pr.registrar(c, st.plan_id, "recuperacion", int(nota.value) * 20,
                             {"cobertura": cob["porcentaje"], "clave": len(cob["clave"])}, tid)
                msg(t("Guardado. Repaso programado: {fecha}", fecha=prox))
                zona.controls = []
                recuerdo.value = ""
                st.page.update()

            chips = [ft.Chip(label=ft.Text(w), leading=ft.Icon(ft.Icons.CHECK, size=16), bgcolor=ft.Colors.GREEN_900) for w in cob["cubiertos"]] + \
                    [ft.Chip(label=ft.Text(w), leading=ft.Icon(ft.Icons.CLOSE, size=16), bgcolor=ft.Colors.RED_900) for w in cob["faltan"]]
            zona.controls = [
                ft.Divider(),
                ft.Text(t("Mencionaste {p}% de las palabras clave de tu referencia", p=cob["porcentaje"]), weight=ft.FontWeight.BOLD),
                ft.ProgressBar(value=cob["porcentaje"] / 100),
                ft.Row(chips, wrap=True, spacing=6, run_spacing=6),
                ft.ExpansionTile(title=ft.Text(t("Ver el texto de referencia")), controls=[
                    ft.Container(ft.Text(texto_ref, selectable=True, size=13), padding=ft.padding.only(left=16, right=16, bottom=12))]),
                *([ft.OutlinedButton(t("✨ Evaluar con IA"), on_click=evaluar), ia_out] if usar_ia else []),
                ft.Text(t("¿Qué tan bien lo recordaste? (0 nada – 5 perfecto)")), nota,
                ft.ElevatedButton(t("Guardar y programar repaso"), icon=ft.Icons.SAVE, on_click=guardar)]
            st.page.update()

        return ft.Column([
            ft.Text(t("Primero intenta recordar sin mirar: es lo que más fija la memoria. Luego compara con tu material."), size=13),
            tema, ref.control, recuerdo,
            ft.ElevatedButton(t("Comparar con mi material"), icon=ft.Icons.COMPARE, on_click=comparar), zona, historial("recuperacion")],
            spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    # ---------- 2 · Feynman ----------
    def pestana_feynman():
        tema = selector_tema()
        ref = Referencia(tema)
        explicacion = ft.TextField(label=t("Explícalo como si hablaras con alguien de {edad} años, sin palabras técnicas", edad=pref["edad"]), multiline=True,
                                   min_lines=8, max_lines=16)
        zona = ft.Column(spacing=8)

        def revisar(_):
            if not explicacion.value.strip():
                return msg(t("Primero escribe tu explicación."), True)
            aviso.value = ""
            referencia = ref.texto()
            r = pr.revisar_explicacion_local(explicacion.value, referencia)
            nota = autoevaluacion()
            ia_out = ft.Column(spacing=4)
            avisos = []
            if r["muy_corta"]:
                avisos.append(t("Es muy corta: si de verdad lo entiendes, deberías poder decir más."))
            if r["largas"]:
                avisos.append(t("Tienes {n} frases muy largas: pártelas en frases más cortas.", n=len(r["largas"])))
            if r["tecnicas"]:
                avisos.append(t("Palabras técnicas que tendrías que explicar: {lista}", lista=", ".join(r["tecnicas"][:8])))
            if r["cobertura"] and r["cobertura"]["faltan"]:
                avisos.append(t("Ideas de tu referencia que no aparecen: {lista}", lista=", ".join(r["cobertura"]["faltan"][:8])))
            usar_ia = ai.ia_disponible()

            def con_ia(_):
                ia_out.controls = [ft.Text(t("La IA está leyendo tu explicación…"), size=12)]
                st.page.update()

                def hacer():
                    try:
                        x = pr.revisar_explicacion_ia(explicacion.value, referencia, edad=pref["edad"])
                        ia_out.controls = [*_lista(t("Quedó claro"), x["claro"], ft.Colors.GREEN_400),
                                           *_lista(t("Huecos"), x["huecos"], ft.Colors.AMBER_400),
                                           *_lista(t("Preguntas de un niño curioso (intenta contestarlas)"), x["preguntas"])]
                    except Exception as ex:
                        ia_out.controls = [ft.Text(t("Error IA: {ex}", ex=ex), color=ft.Colors.RED_300, size=12)]
                    st.page.update()
                threading.Thread(target=hacer, daemon=True).start()

            def guardar(_):
                tid = int(tema.value)
                prox = repo.guardar_nota(c, tid, explicacion.value.strip(), int(nota.value))
                pr.registrar(c, st.plan_id, "feynman", int(nota.value) * 20, {"palabras": r["palabras"]}, tid)
                msg(t("Guardado. Repaso programado: {fecha}", fecha=prox))
                zona.controls = []
                explicacion.value = ""
                st.page.update()

            zona.controls = [
                ft.Divider(),
                ft.Text(tn(r["palabras"], "{n} palabra, {f} frases.", "{n} palabras, {f} frases.", f=r["frases"]), size=12),
                *(_lista(t("Para mejorarla"), avisos, ft.Colors.AMBER_400) or [ft.Text(t("Se ve sencilla y completa."), color=ft.Colors.GREEN_400)]),
                *([ft.OutlinedButton(t("✨ Revisar con la IA (como un niño curioso)"), on_click=con_ia), ia_out] if usar_ia else
                  [ft.Text(t("Con una IA configurada también puedo hacerte preguntas como un niño curioso."), size=12)]),
                ft.Text(t("¿Qué tan bien lo recordaste? (0 nada – 5 perfecto)")), nota,
                ft.ElevatedButton(t("Guardar y programar repaso"), icon=ft.Icons.SAVE, on_click=guardar)]
            st.page.update()

        return ft.Column([
            ft.Text(t("Si no puedes explicarlo con palabras sencillas, aún no lo entiendes del todo. Escríbelo y revísalo."), size=13),
            tema, ref.control, explicacion,
            ft.ElevatedButton(t("Revisar mi explicación"), icon=ft.Icons.RATE_REVIEW, on_click=revisar), zona, historial("feynman")],
            spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    # ---------- 3 · simulacro ----------
    def pestana_simulacro():
        cuerpo = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
        est = {"gen": 0}
        tema = selector_tema()
        alcance = ft.Dropdown(label=t("Qué entra en el examen"), width=260, value="plan",
                              options=[ft.dropdown.Option(k, t(v)) for k, v in ALCANCES.items()])
        n_preg = ft.Dropdown(label=t("Preguntas"), width=130, value=str(pref["simulacro"][0]), options=[ft.dropdown.Option(str(x)) for x in (5, 10, 20, 30, 50)])
        minutos = ft.Dropdown(label=t("Tiempo"), width=170, value=str(pref["simulacro"][1]), options=[
            ft.dropdown.Option("0", t("Sin límite"))] + [ft.dropdown.Option(str(x), t("{n} min", n=x)) for x in (5, 10, 15, 20, 30, 60)])
        tipo = ft.Dropdown(label=t("Tipo de preguntas"), width=210, value="mixto",
                           options=[ft.dropdown.Option(k, t(v)) for k, v in TIPOS_SIMULACRO.items()])

        def inicio(_=None):
            est["gen"] += 1
            cuerpo.controls = [
                ft.Text(t("Un examen con tus propias tarjetas y el reloj en marcha. Lo que falles volverá pronto a tu repaso."), size=13),
                ft.Row([tema, alcance], wrap=True), ft.Row([n_preg, minutos, tipo], wrap=True),
                ft.ElevatedButton(t("Empezar el simulacro"), icon=ft.Icons.PLAY_ARROW, on_click=empezar), historial("simulacro")]
            st.page.update()

        def empezar(_):
            a = alcance.value
            ids = errores.ids_de_refuerzo(c, st.perfil_id, st.plan_id, int(n_preg.value)) if a == "debiles" else None
            if a == "debiles" and not ids:
                return msg(t("Aún no hay suficientes repasos para saber cuáles son tus puntos débiles."), True)
            preguntas = pr.preparar_simulacro(c, st.perfil_id, None if a == "todas" else st.plan_id,
                                              int(tema.value) if a == "tema" else None, int(n_preg.value), tipo.value, ids=ids)
            if not preguntas:
                return msg(t("No hay tarjetas para examinarte. Crea tarjetas en «Estudiar» o en «Material»."), True)
            aviso.value = ""
            examen(preguntas, int(minutos.value) * 60)

        def examen(preguntas, segundos):
            est["gen"] += 1
            gen, inicio_t = est["gen"], time.time()
            resp: dict = {}
            pos = {"i": 0}
            reloj = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
            zona = ft.Column(spacing=10)

            def terminar(_=None):
                if est["gen"] != gen:
                    return
                est["gen"] += 1
                resultado(preguntas, resp, int(time.time() - inicio_t))

            def dibujar():
                p = preguntas[pos["i"]]
                zona.controls = [ft.Text(t("Pregunta {i} de {n}", i=pos["i"] + 1, n=len(preguntas)), size=12, color=ft.Colors.OUTLINE),
                                 texto_tarjeta(p.enunciado, size=18, weight=ft.FontWeight.W_500)]
                if p.opciones:
                    grupo = ft.RadioGroup(value=resp.get(p.tarjeta_id), on_change=lambda e, p=p: resp.__setitem__(p.tarjeta_id, e.control.value),
                                          content=ft.Column([ft.Radio(value=o, label=pr.plano(o)) for o in p.opciones]))
                    zona.controls.append(grupo)
                else:
                    correcta = texto_tarjeta(p.correcta, size=15, selectable=True, visible=False)
                    juicio = ft.Row([ft.ElevatedButton(t("Acerté"), icon=ft.Icons.CHECK, on_click=lambda _, p=p: (resp.__setitem__(p.tarjeta_id, True), siguiente())),
                                     ft.OutlinedButton(t("Fallé"), icon=ft.Icons.CLOSE, on_click=lambda _, p=p: (resp.__setitem__(p.tarjeta_id, False), siguiente()))],
                                    visible=False)

                    def mostrar(e):
                        correcta.visible = juicio.visible = True
                        e.control.visible = False
                        st.page.update()
                    zona.controls += [ft.TextButton(t("Mostrar respuesta (intenta recordar primero)"), on_click=mostrar), correcta, juicio]
                ultima = pos["i"] == len(preguntas) - 1
                zona.controls.append(ft.Row([
                    ft.OutlinedButton(t("Anterior"), icon=ft.Icons.NAVIGATE_BEFORE, on_click=lambda _: ir(-1), disabled=pos["i"] == 0),
                    ft.ElevatedButton(t("Terminar"), icon=ft.Icons.FLAG, on_click=terminar) if ultima else
                    ft.OutlinedButton(t("Siguiente"), icon=ft.Icons.NAVIGATE_NEXT, on_click=lambda _: ir(1))], wrap=True))
                st.page.update()

            def ir(d):
                pos["i"] = max(0, min(len(preguntas) - 1, pos["i"] + d))
                dibujar()

            def siguiente():
                if pos["i"] < len(preguntas) - 1:
                    ir(1)
                else:
                    terminar()

            def cuenta():
                while est["gen"] == gen:
                    resto = segundos - int(time.time() - inicio_t) if segundos else None
                    reloj.value = f"⏱ {resto // 60:02d}:{resto % 60:02d}" if resto is not None else f"⏱ {int(time.time() - inicio_t) // 60:02d}:{int(time.time() - inicio_t) % 60:02d}"
                    st.page.update()
                    if resto is not None and resto <= 0:
                        terminar()
                        return
                    time.sleep(1)

            cuerpo.controls = [ft.Row([reloj, ft.TextButton(t("Terminar ahora"), on_click=terminar)], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), zona]
            dibujar()
            threading.Thread(target=cuenta, daemon=True).start()

        def resultado(preguntas, resp, seg):
            r = pr.corregir(preguntas, resp)
            pr.reprogramar_errores(c, r["errores"])
            pr.registrar(c, st.plan_id, "simulacro", r["porcentaje"],
                         {"n": r["total"], "correctas": r["correctas"], "segundos": seg, "errores": [p.tarjeta_id for p in r["errores"]]},
                         int(tema.value) if alcance.value == "tema" else None)
            color = ft.Colors.GREEN_400 if r["porcentaje"] >= 70 else ft.Colors.AMBER_400 if r["porcentaje"] >= 50 else ft.Colors.RED_300
            fallos = []
            for p in r["errores"]:
                dada = resp.get(p.tarjeta_id)
                fallos.append(ft.Container(ft.Column([
                    texto_tarjeta(p.enunciado, size=14, weight=ft.FontWeight.W_500),
                    ft.Row([ft.Text(t("Correcta:"), size=12, color=ft.Colors.GREEN_400), texto_tarjeta(p.correcta, size=13, selectable=True)], wrap=True),
                    *([ft.Text(t("Tu respuesta: {x}", x=pr.plano(dada)), size=12, color=ft.Colors.RED_300)] if p.opciones and dada else [])],
                    spacing=2), padding=10, border_radius=8, border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT)))
            cuerpo.controls = [
                ft.Text(f"{r['porcentaje']}%", size=48, weight=ft.FontWeight.BOLD, color=color),
                ft.Text(t("{a} de {b} correctas · {m:02d}:{s:02d}", a=r["correctas"], b=r["total"], m=seg // 60, s=seg % 60)),
                ft.Text(tn(len(r["errores"]), "{n} tarjeta fallada vuelve a tu repaso.", "{n} tarjetas falladas vuelven a tu repaso."), size=13)
                if r["errores"] else ft.Text(t("¡Sin errores! 🎉"), size=13),
                *([ft.Text(t("Para repasar los errores"), weight=ft.FontWeight.BOLD)] + fallos if fallos else []),
                ft.Row([ft.ElevatedButton(t("Otro simulacro"), icon=ft.Icons.REPLAY, on_click=inicio),
                        ft.OutlinedButton(t("Ir a Repaso"), icon=ft.Icons.STYLE, on_click=lambda _: ir_a_repaso())], wrap=True)]
            st.page.update()

        def refuerzo():
            alcance.value = "debiles"
            empezar(None)

        compartido["refuerzo"] = refuerzo
        inicio()
        return cuerpo

    # ---------- 4 · puntos débiles (diario de errores) ----------
    def pestana_debiles():
        cuerpo = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
        debiles = errores.puntos_debiles(c, st.perfil_id, st.plan_id)
        dificiles = errores.tarjetas_dificiles(c, st.perfil_id, st.plan_id)

        def lanzar(_):
            compartido["tabs"].selected_index = 2
            st.page.update()
            compartido["refuerzo"]()

        cuerpo.controls = [ft.Text(t("Lo que más conviene estudiar: aquello que fallas. Se calcula con tus repasos y prácticas de los últimos meses."), size=13)]
        if not debiles and not dificiles:
            cuerpo.controls.append(ft.Text(t("Aún no hay suficientes repasos para saber cuáles son tus puntos débiles. Repasa unos días y vuelve."), color=ft.Colors.OUTLINE))
        if debiles:
            cuerpo.controls += [ft.Text(t("Temas que más fallas"), weight=ft.FontWeight.BOLD, size=13)]
            for d in debiles:
                cuerpo.controls += [
                    ft.Text(f"{d['tema']} · {d['plan']}", size=13),
                    ft.ProgressBar(value=min(1, d["tasa_fallo"]), color=ft.Colors.RED_300),
                    ft.Text(t("{p}% de fallos en {n} repasos", p=round(d["tasa_fallo"] * 100), n=d["repasos"]) +
                            (" · " + t("práctica: {p}%", p=d["practica"]) if d["practica"] is not None else ""), size=11, color=ft.Colors.OUTLINE)]
        if dificiles:
            cuerpo.controls += [ft.Text(t("Tarjetas que más te cuestan"), weight=ft.FontWeight.BOLD, size=13)]
            for d in dificiles[:8]:
                cuerpo.controls += [ft.Container(ft.Column([
                    texto_tarjeta(d["pregunta"], size=14), ft.Text(t("{a} fallos en {b} repasos", a=d["fallos"], b=d["repasos"]), size=11, color=ft.Colors.RED_300)],
                    spacing=2), padding=8, border_radius=8, border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT))]
        if debiles or dificiles:
            cuerpo.controls.append(ft.ElevatedButton(t("Hacer un refuerzo de mis puntos débiles"), icon=ft.Icons.FITNESS_CENTER, on_click=lanzar))
        return cuerpo

    abiertas = {"recuperacion": pestana_recuperacion, "feynman": pestana_feynman, "simulacro": pestana_simulacro}
    tabs = ft.Tabs(selected_index=0, expand=1, tabs=[ft.Tab(text=t(v), content=ft.Container(abiertas[k](), padding=ft.padding.only(top=12)))
                                                      for k, v in NOMBRES_TIPO.items()] +
                   [ft.Tab(text=t("Puntos débiles"), content=ft.Container(pestana_debiles(), padding=ft.padding.only(top=12)))])
    compartido["tabs"] = tabs
    if st.pestana_practica is not None:        # llegamos desde un paso del sprint
        tabs.selected_index, st.pestana_practica = st.pestana_practica, None
    return ft.Column([ft.Text(t("Práctica activa"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL), aviso, tabs], spacing=8, expand=True)
