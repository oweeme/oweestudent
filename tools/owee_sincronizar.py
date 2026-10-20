"""Genera el catálogo Owee de la interfaz a partir del repositorio del idioma (https://github.com/oweeme/owee).

    python tools/owee_sincronizar.py /ruta/al/repositorio/owee

Lee `08_Integracion/datos/ui_glosario.tsv` (en · es · owee) y los léxicos de `02_Diccionario/datos/`.
Solo se usan términos que YA están en el glosario: la app no inventa palabras Owee. Escribe
`i18n/catalogos/qow.py` (textos traducidos) y `i18n/datos/owee_vocabulario.txt` (palabras aprobadas, que
vigila `tests/test_owee.py`). Para ampliar la cobertura, añade términos al glosario de Owee y vuelve a ejecutar.
"""
import csv
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

# Equivalencias a mano entre el inglés de la app y el inglés del glosario (solo las seguras).
SINONIMOS = {"sign in": "log in", "sign out": "log out", "auto": "automatic", "install": "install"}
# Coinciden en inglés pero no en sentido: «ligero» (poco peso) no es «light» (claro).
EXCLUIR = {"ligero"}


def normalizar(s: str) -> str:
    s = re.sub(r"[^a-z' ]", "", s.lower()).strip()
    return SINONIMOS.get(s, s)


def main(repo: Path):
    from i18n.catalogos.en import TEXTOS as EN
    glos = {}
    with open(repo / "08_Integracion/datos/ui_glosario.tsv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            glos[normalizar(r["en"])] = r["owee"].strip()
    textos = {}
    for es, en in EN.items():
        if es in EXCLUIR or isinstance(en, tuple):
            continue
        o = glos.get(normalizar(en))
        if o:
            textos[es] = o
    palabras = set()
    for nombre in ("lexico.tsv", "lexico_ciencias.tsv"):
        with open(repo / "02_Diccionario/datos" / nombre, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                palabras.add(r["owee"].strip().lower())
    for o in glos.values():
        palabras.update(o.lower().split())
    (RAIZ / "i18n/datos").mkdir(exist_ok=True)
    (RAIZ / "i18n/datos/owee_vocabulario.txt").write_text("\n".join(sorted(p for p in palabras if p)) + "\n", encoding="utf-8")
    lineas = ['"""Owee (código qow, romanización). Generado por tools/owee_sincronizar.py a partir del glosario de Owee',
              '(https://github.com/oweeme/owee, CC BY-SA 4.0). No lo edites a mano: amplía el glosario y vuelve a generarlo."""',
              "TEXTOS = {"]
    lineas += [f"    {k!r}: {v!r}," for k, v in textos.items()]
    lineas.append("}")
    (RAIZ / "i18n/catalogos/qow.py").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print(f"{len(textos)} textos Owee de {len(EN)} · {len(palabras)} palabras aprobadas")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
