"""Exámenes modelo de la certificación de Owee (https://github.com/oweeme/owee, `03_Material_Ensenanza/Certificacion/`).

Contenido: Hector Martinez (CC BY-SA 4.0). Esto es un SIMULACRO para prepararte: el certificado oficial lo da un examinador
y solo es válido si su código figura en el registro público de oweeme.github.io/owee.

Cada examen tiene partes (A Escuchar, B Leer, C Escribir, D Gramática y vocabulario, E Hablar, F Números, G Explicar y crear).
En el simulacro: lo que tiene una respuesta exacta en Owee se corrige solo (`auto`); lo demás muestra la clave y tú te
puntúas. «Escuchar» y «Hablar» los hace en persona un examinador; aquí se adaptan (leer el texto; hablar en voz alta).
"""

from i18n import marcar

SEMILLA, BROTE, ARBOL, N0, N1, N2, N3, N4 = "semilla", "brote", "arbol", "nivel0", "nivel1", "nivel2", "nivel3", "nivel4"


def _it(enunciado, puntos, clave="", auto=None, owee=None, glifos=None, voz=False, valorar=False):
    """Un ejercicio. `auto`: respuestas aceptadas (se compara sin mayúsculas, espacios ni guiones). `owee`: líneas de texto a leer
    (se muestran en glifos y romano). `glifos`: palabras que se muestran solo en glifos. `voz`: se hace en voz alta."""
    return {"enunciado": enunciado, "puntos": puntos, "clave": clave, "auto": auto, "owee": owee or [], "glifos": glifos or [],
            "voz": voz, "valorar": valorar}


def _parte(id_, nombre, items, examinador=False):
    return {"id": id_, "nombre": nombre, "puntos": sum(i["puntos"] for i in items), "items": items, "examinador": examinador}


EXAMENES = {
    SEMILLA: {"titulo": "Infantil 1 — Semilla", "ruta": "infantil", "edad": "5–7 años", "minutos": 25, "aprobar": {"parte": 3}, "nivel_curso": 0,
              "partes": [
                  _parte("A", marcar("Escuchar"), [_it("Un adulto dice la palabra dos veces y tú señalas el dibujo. Dime en voz alta qué significa: `suna`, `sade`, `maku`, `loke`, `kuma`.", 5,
                                               "agua · sol · mano · ojo · casa", voz=True)], True),
                  _parte("B", marcar("Leer"), [_it("Lee en voz alta estas sílabas y palabras:", 5, "Acento en la primera sílaba: NA-ra, SU-na, ME-la.", voz=True,
                                           owee=["a e o u pa me nara suna mela"])]),
                  _parte("C", marcar("Escribir"), [_it("Mira los glifos y escribe en romano las cuatro vocales:", 3, "a e o u", ["a e o u"], glifos=["a e o u"]),
                                           _it("Mira los glifos y escribe en romano las dos palabras:", 2, "suna kuma", ["suna kuma"], glifos=["suna kuma"])]),
                  _parte("E", marcar("Hablar"), [_it("Di en voz alta: «yo», «tú», tres palabras de tu familia o tu casa y pide agua en Owee.", 5, "me · tu · me suna nume", voz=True)], True),
                  _parte("F", marcar("Números"), [_it("Cuenta del 0 al 10 en Owee y lee 3, 7 y 10.", 3, "cho be du ga fo sa ku mu na she tanu", voz=True),
                                          _it("¿Cuántos son 2 + 1? Escribe la cifra:", 2, "3", ["3"])]),
              ]},
    BROTE: {"titulo": "Infantil 2 — Brote", "ruta": "infantil", "edad": "8–9 años", "minutos": 25, "aprobar": {"parte": 3}, "nivel_curso": 1,
            "partes": [
                _parte("A", marcar("Escuchar"), [
                    _it("Lee el texto. ¿Dónde está la persona?", 2, "En casa (`kuma bo`)", owee=["me kuma bo mora", "me suna nobe pume", "me tase nume"]),
                    _it("¿Qué bebe?", 1, "Agua"), _it("¿Qué quiere hacer?", 2, "Aprender (`tase`)")], True),
                _parte("B", marcar("Leer"), [_it(f"Une con su significado ({l}): a) Comí. b) ¿Quieres agua? c) Quiero agua. d) Estoy en casa. e) Querrá dormir. Escribe la letra:", 1, "", [r], owee=[o])
                                     for l, o, r in (("1", "me suna nume", "c"), ("2", "me fame pe pume", "a"), ("3", "ra sule pu nume", "e"),
                                                     ("4", "me kuma bo", "d"), ("5", "tu suna nume ka", "b"))]),
                _parte("C", marcar("Escribir"), [_it("Mira y copia en romano:", 2, "mela sade nelo", ["mela sade nelo"], glifos=["mela sade nelo"]),
                                         _it("Escribe en Owee: «Quiero comida».", 2, "me fame nume", ["me fame nume"]),
                                         _it("Escribe una pregunta con `ka`.", 1, "Por ejemplo: tu fame nume ka")]),
                _parte("E", marcar("Hablar"), [_it("Conversa en voz alta (4 turnos): reme · tu sado ka · tu suna nume ka · pu-reme.", 5,
                                           "Hola. ¿Estás bien? ¿Quieres agua? Adiós.", voz=True)], True),
                _parte("F", marcar("Números"), [_it("Lee en voz alta: 15 · 42 · 100.", 2, "", voz=True, owee=["15 42 100"]),
                                        _it("Calcula 6 + 3, 9 − 4 y 2 × 5 (escribe las tres cifras):", 3, "9 · 5 · 10", ["9 5 10"])]),
            ]},
    ARBOL: {"titulo": "Infantil 3 — Árbol", "ruta": "infantil", "edad": "10–12 años", "minutos": 30, "aprobar": {"parte": 6}, "nivel_curso": 1,
            "partes": [
                _parte("A", marcar("Escuchar"), [_it(q, 2.5, c, owee=(["ruma-kuna suna nume", "suna lu mora", "ruma-suna galo", "ruma-kuna pe nobe pume", "ruma-kuna lena"] if i == 0 else None))
                                         for i, (q, c) in enumerate((("Lee el cuento. ¿Quién quería agua?", "El pájaro"), ("¿Dónde estaba el agua?", "Lejos (`lu`)"),
                                                                      ("¿Quién ayudó?", "El pez"), ("¿Cómo terminó el pájaro?", "Contento (`lena`)")))], True),
                _parte("B", marcar("Leer"), [_it(q, 2.5, c, owee=(["me mela kuma bo mora", "me pade fame pume", "me naku suna nobe pume", "me sare sule", "kuna-bore te mora", "me sule nume"] if i == 0 else None))
                                     for i, (q, c) in enumerate((("¿Quién come?", "El progenitor (`me pade`)"), ("¿Quién duerme?", "El hermano (`me sare`)"),
                                                                  ("¿Es de día o de noche?", "De noche (`kuna-bore`)"), ("¿Qué quiere hacer quien habla?", "Dormir")))]),
                _parte("C", marcar("Escribir"), [_it("Escribe cuatro frases sobre ti en romano: tu familia, tu casa, lo que te gusta y lo que harás mañana (`pu-fusu`).", 10,
                                             "Se valora: frases correctas, vocabulario, el futuro con `pu`.", valorar=True)]),
                _parte("E", marcar("Hablar"), [_it("Conversa en voz alta (6 turnos): preséntate (`me sena-nara …`), di tu edad, tu familia, una comida favorita, un plan y despídete.", 10, voz=True,
                                           clave="Preséntate, familia, comida, plan y despedida con las palabras del curso.")], True),
                _parte("F", marcar("Números"), [_it("Lee en voz alta: 247 · 1000 · 2026.", 3, "", voz=True, owee=["247 1000 2026"]),
                                        _it("Calcula 7 × 8, 36 ÷ 6 y 50 − 25 (escribe las tres cifras):", 4, "56 · 6 · 25", ["56 6 25"]),
                                        _it("Escribe un medio como fracción y como decimal.", 3, "1/2 y 0.5", voz=False)]),
            ]},
    N0: {"titulo": "Nivel 0 — Inicial", "ruta": "adultos", "edad": "13+ años", "minutos": 30, "aprobar": {"total": 0.7, "parte": 0.5}, "nivel_curso": 0,
         "partes": [
             _parte("A", marcar("Escuchar"), [_it("Mira los glifos y escribe la sílaba en romano:", 1, "", [s], glifos=[s]) for s in ("ma", "ke", "sho", "ru")], True),
             _parte("B", marcar("Leer"), [_it("Lee en voz alta, con el acento en la primera sílaba:", 4, "SU-na · KU-ma · NA-ra · SA-de-SA-lo · PO-re · MU-ne · TA-ro · SU-ra", voz=True,
                                      owee=["suna kuma nara sade-salo pore mune taro sura"])]),
             _parte("C", marcar("Escribir"), [_it("Escribe en romano las cuatro vocales de Owee.", 2, "a e o u", ["a e o u"]),
                                      _it("Mira los glifos y cópialos en romano:", 2, "pa be sho chu nara sade-kelo", ["pa be sho chu nara sade-kelo"], glifos=["pa be sho chu nara sade-kelo"])]),
             _parte("D", marcar("Gramática y vocabulario"), [
                 _it("¿Cuántas vocales tiene Owee? ¿Cuál no existe?", 1, "4 vocales (a e o u); no existe la `i`."),
                 _it("¿Qué significa `suna`? ¿Y `kuma`?", 1, "agua · casa"),
                 _it("¿Dónde va el acento en `sade-kelo`?", 1, "En la primera sílaba de cada elemento (SA-de-KE-lo)."),
                 _it("¿Qué une el nexo ‿ en Owee Script?", 1, "Los elementos de un compuesto.")]),
             _parte("F", marcar("Números"), [_it("Escribe en romano cómo se dicen 7, 12 y 20:", 2, "mu · be tanu du · du tanu", ["mu be tanu du du tanu"]),
                                     _it("Escribe con glifos 5, 14 y 18 (comprueba con la tabla de la lección 0.4).", 1, "Consulta los números de la lección 0.4."),
                                     _it("Lee en voz alta la cuenta 2 + 3 = 5.", 1, "Con los nombres de los números de la lección 0.4.", voz=True)]),
         ]},
    N1: {"titulo": "Nivel 1 — Primeras frases (A1)", "ruta": "adultos", "edad": "13+ años", "minutos": 60, "aprobar": {"total": 0.7, "parte": 0.5}, "nivel_curso": 1,
         "partes": [
             _parte("A", marcar("Escuchar"), [_it(q, 2, c, owee=(["me mela kuma bo mora", "me pade fame pume", "me naku suna nobe pume", "kuna-bore te mora", "me sule nume"] if i == 0 else None))
                                      for i, (q, c) in enumerate((("Lee el texto. ¿Dónde está la familia?", "En casa"), ("¿Quién come?", "El progenitor"), ("¿Qué bebe el hijo?", "Agua"),
                                                                   ("¿Es de día o de noche?", "De noche"), ("¿Qué quiere hacer quien habla?", "Dormir")))], True),
             _parte("B", marcar("Leer"), [_it(f"Traduce al español: `{o}`", p, c, owee=[o]) for o, p, c in (
                 ("me kuma gore-pa", 2, "Mi casa es grande"), ("me kuma bo mora", 2, "Estoy en casa"), ("ra pe fame pume", 2, "Él comió"),
                 ("tu pu duma ka", 2, "¿Te irás?"), ("suna lu", 1, "El agua está lejos"), ("me suna no nume", 1, "No quiero agua"))]),
             _parte("C", marcar("Escribir"), [_it(f"Escribe en Owee: {e}", 2, c, [c]) for e, c in (
                 ("«Quiero agua.»", "me suna nume"), ("«¿Quieres comida?»", "tu fame nume ka"), ("«Mi casa es grande.»", "me kuma gore-pa"),
                 ("«Él durmió.»", "ra pe sule"), ("«¿Dónde estás?»", "tu ka-kore mora"))]),
             _parte("D", marcar("Gramática y vocabulario"), [
                 _it("Pon en orden: `nume` · `me` · `fame`", 2, "me fame nume", ["me fame nume"]),
                 _it("Haz negativa: `ra sule`", 2, "ra no sule", ["ra no sule"]),
                 _it("Pasa al futuro: `me daro`", 2, "me pu daro", ["me pu daro"]),
                 _it("¿Por qué `tu ka-kore mora` no lleva `ka` al final?", 1, "Porque la palabra de pregunta ya marca la pregunta."),
                 _it("Opuestos: `fure-pa` / ____ · `gore-pa` / ____", 1, "fure-po · gore-po", ["fure-po gore-po"]),
                 _it("Colores: rojo · verde · blanco", 1, "rale · nede · fale", ["rale nede fale"]),
                 _it("Partes del cuerpo: mano · ojo · boca", 1, "maku · loke · sabe", ["maku loke sabe"])]),
             _parte("E", marcar("Hablar"), [_it("Conversa en voz alta (6 turnos): saluda, di cómo estás, presenta a tu familia, di dónde vives, qué quieres y despídete.", 10, voz=True,
                                        clave="Usa `reme`, `me sado`, `me kuma bo`, `me ... nume`, `pu-reme`.")], True),
         ]},
    N2: {"titulo": "Nivel 2 — Conversar (A2)", "ruta": "adultos", "edad": "13+ años", "minutos": 105, "aprobar": {"total": 0.7, "parte": 0.5}, "nivel_curso": 2,
         "partes": [
             _parte("A", marcar("Escuchar"), [_it(q, 3, c, owee=(["reme", "reme", "me nelo-fame nume", "tu ka-bema nume", "du", "du nelo-fame, sa fedo", "tare, gura-lena", "pu-reme"] if i == 0 else None))
                                      for i, (q, c) in enumerate((("Lee el diálogo. ¿Qué quiere comprar la persona?", "Fruta"), ("¿Cuántos compra?", "Dos"),
                                                                   ("¿Es caro o barato?", "Barato: cinco de pago"), ("¿Cómo se despiden?", "`gura-lena`, `pu-reme`")))], True),
             _parte("B", marcar("Leer"), [_it(q, 3, c, owee=(["te-fusu me geru bo kuma-seta to duma", "me pegu bo shuse", "pu-fusu me pade-bufu nosho mora", "me lena-tabu kera-fedo nume",
                                                      "balo-ke bado-pa, me pase pode"] if i == 0 else None))
                                  for i, (q, c) in enumerate((("¿Adónde va quien escribe y cómo?", "A la ciudad, en coche (y llama por teléfono)"),
                                                               ("¿Qué pasa mañana?", "Es el cumpleaños de su mamá"), ("¿Qué quiere comprar?", "Un pastel"),
                                                               ("¿Qué problema tiene y qué decide?", "Es caro, aunque puede comprarlo")))]),
             _parte("C", marcar("Escribir"), [_it("Escribe un mensaje de 5 a 6 frases a un amigo (en romano): invítalo a tu cumpleaños, di el día, qué habrá de comer y pídele una respuesta.", 12,
                                          "Se valora: frases correctas, vocabulario del nivel, futuro con `pu`, cortesía.", valorar=True)]),
             _parte("D", marcar("Gramática y vocabulario"), [
                 _it("«Nadie come»", 1.5, "nara-no pume", ["nara-no pume"]), _it("«Tengo tres hijos»", 1.5, "me ga naku pase", ["me ga naku pase"]),
                 _it("«Él es más grande que yo»", 1.5, "ra me gore-pa", ["ra me gore-pa"]), _it("«¿Puedes darme agua?» (con cortesía)", 1.5, "tu suna pema pode ka", ["tu suna pema pode ka"]),
                 _it("«Hoy», «ayer» y «mañana»", 1.5, "te-fusu · pe-fusu · pu-fusu", ["te-fusu pe-fusu pu-fusu"]),
                 _it("Escribe el imperativo de «dormir» y úsalo con vocativo.", 1.5, "sule · naku, sule", ["sule naku sule", "naku sule"]),
                 _it("Explica `mu-fusu`.", 1.5, "Siete días: una semana."), _it("«Muy grande»", 1.5, "gore-pa-pa", ["gore-pa-pa"])]),
             _parte("E", marcar("Hablar"), [_it("Juego de roles en voz alta (8 turnos): en el mercado o de viaje, saluda, pregunta el precio, pide con cortesía, acepta o rechaza, agradece y despídete.", 12,
                                        "Usa `pema`, `pode`, `gura-lena`, `pu-reme`.", voz=True)], True),
         ]},
    N3: {"titulo": "Nivel 3 — Leer y crear (B1)", "ruta": "adultos", "edad": "13+ años", "minutos": 105, "aprobar": {"total": 0.7, "parte": 0.5}, "nivel_curso": 3,
         "partes": [
             _parte("A", marcar("Escuchar"), [_it("Lee el texto y resume en español qué ocurre y quiénes participan.", 14,
                                          "El pájaro se movió y quería agua; el agua estaba lejos. Preguntó dónde estaba; el pez le dijo que estaba aquí. El pájaro bebió y quedó contento.",
                                          owee=["ruma-kuna pe duma", "ruma-kuna suna nume", "suna lu", "ruma-kuna pe reka", "suna ka-kore", "ruma-suna pe reka", "suna kore-le mora",
                                                "ruma-kuna pe nobe pume", "ruma-kuna lena"])], True),
             _parte("B", marcar("Leer"), [_it("Traduce las dos primeras líneas y explica qué hace `ra`.", 5, "«La persona que quiere agua es mi amiga» · «La casa que vi es grande»: `ra` repite el nombre dentro de la oración subordinada.",
                                      owee=["nara, ra suna nume, me reme", "kuma, me ra pe luma-salo, gore-pa", "ke tu suna pema, ra malo", "ruma-pore bade-kuma go kuna-duma", "fokoro-nara fokoro-reka reka"]),
                                  _it("¿Qué expresa `ke` en la tercera línea?", 4, "Una condición («si le das agua, queda en calma»)."),
                                  _it("Traduce las dos últimas líneas.", 5, "«El dragón vuela sobre el castillo» · «El mago dice un hechizo»")]),
             _parte("C", marcar("Escribir"), [_it("Escribe un texto de 10 a 12 líneas en romano: un cuento breve, una carta o la descripción de un tema de ciencia. Usa al menos dos compuestos, una relativa con `ra`, pasado y futuro.",
                                          14, "Se valora: corrección, variedad (compuestos, `ra`, `pe`, `pu`) y claridad.", valorar=True)]),
             _parte("D", marcar("Gramática y vocabulario"), [
                 _it("Forma con raíces existentes y explica: «lugar de libros», «agua grande», «máquina de cocinar».", 2, "lodu-kuma (biblioteca) · suna-gore-pa (mar) · pore-meka (estufa). Ya existen; un compuesto nuevo bien formado también vale."),
                 _it("¿Por qué `tomate` no es una palabra Owee válida aunque cumple la fonología?", 2, "Copia una palabra española: el significado ya tiene raíz (`muru`)."),
                 _it("Adapta como nombres propios: Carlos, Lucía, Bolivia.", 2, "Karaloso · Lusea · Bolebea", ["karaloso lusea bolebea"]),
                 _it("Di el plural de `kuma` y explica por qué.", 2, "No cambia: Owee no marca el número (`du kuma`, «dos casas»)."),
                 _it("Explica la diferencia entre `sade-kelo` y `sade kelo`.", 2, "Compuesto («año») frente a frase («sol, ciclo»)."),
                 _it("Escribe en romano la lectura de 2026 y de 3/4.", 2, "du soku du tanu ku · ga palo fo", ["du soku du tanu ku ga palo fo"]),
                 _it("Palabras de enlace: «aunque», «pronto», «todavía».", 2, "balo-ke · pu-le · te-dure", ["balo-ke pu-le te-dure"])]),
             _parte("E", marcar("Hablar"), [_it("Presenta en voz alta durante 3 minutos un tema (tu trabajo, tu ciudad, un libro) y responde dos preguntas.", 14, voz=True,
                                        clave="Claridad, vocabulario del nivel y pronunciación con acento inicial.")], True),
         ]},
    N4: {"titulo": "Nivel 4 — Dominio (B2)", "ruta": "adultos", "edad": "13+ años", "minutos": 140, "aprobar": {"total": 0.7, "parte": 0.5}, "nivel_curso": 3,
         "partes": [
             _parte("A", marcar("Escuchar"), [_it("Lee un mito o cuento de la *Literatura* de Owee. Resume la historia, los personajes y la idea central (`soma-choma`).", 15, "La idea central, los personajes y el desenlace.")], True),
             _parte("B", marcar("Leer"), [_it("Lee una sección de una guía de ciencias (*Física*, *Química* o *Matemáticas*) y explica con tus palabras, en Owee, tres conceptos.", 15,
                                      "Tres conceptos explicados con vocabulario Owee correcto.", valorar=True)]),
             _parte("C", marcar("Escribir"), [_it("Escribe un texto de 25 líneas o más en romano: una carta formal, un relato de fantasía o un artículo de divulgación.", 20,
                                          "Se valora: corrección, variedad (compuestos, relativas, enlaces, tiempos) y claridad.", valorar=True)]),
             _parte("D", marcar("Gramática y vocabulario"), [
                 _it("Corrige y explica los errores: `me ka-kore mora ka` · `ra sueno nume` · `tomate pume` · `me pe suna nume pu`", 4,
                     "`tu ka-kore mora` (con palabra de pregunta no va `ka` final) · `ra sule-soma nume` («quiere soñar») · `muru pume` · el tiempo va antes del verbo y una vez: `me pe suna nume`."),
                 _it("Traduce al Owee: «Aunque llueve, mañana viajaremos a la playa; quizás veamos delfines».", 4,
                     "Modelo: `balo-ke kuna-suna mora, pu-fusu mene dutude to pubu; sufugo mene somase luma-salo`. Se aceptan variantes correctas."),
                 _it("Traduce al español: `kuma, me ra bo suma, gule` · `nara-fese suna nume` · `me rena-se, balo-ke bumosa dema-pa`", 4,
                     "«La casa donde vivo es vieja» · «Todos quieren agua» · «Estoy de acuerdo, aunque el problema es difícil»"),
                 _it("Explica por qué no quedan raíces de 2 sílabas y qué se hace en su lugar.", 3,
                     "Cada raíz de 2 sílabas debe estar a 2 letras o más de todas las demás para no confundirse al oído; ese espacio se agotó. Las nuevas son de 3 sílabas y lo demás son compuestos de 2 elementos.")]),
             _parte("E", marcar("Hablar"), [_it("Debate en voz alta (10 minutos) sobre un tema de la vida pública (educación, trabajo, ciencia, ambiente).", 15, voz=True,
                                        clave="Argumenta con claridad, corrección y vocabulario variado.")], True),
             _parte("G", marcar("Explicar y crear"), [
                 _it("Propón tres palabras nuevas para un oficio o una región que conozcas y compruébalas (forma, partes, sílabas).", 10,
                     "Comprueba cada una en la página «Crear palabras» del sitio: forma, significado, partes, sílabas y avisos."),
                 _it("Explica a un principiante la diferencia entre `mora`, `pase` y el poseedor delante (`me kuma`).", 10,
                     "Explícalo en Owee y en español, con ejemplos correctos.")]),
         ]},
}

ORDEN = [SEMILLA, BROTE, ARBOL, N0, N1, N2, N3, N4]
