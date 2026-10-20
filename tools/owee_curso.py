"""Genera el paquete del curso de Owee (`owee_curso/datos.py`) a partir del repositorio del idioma
(https://github.com/oweeme/owee): lecciones de `03_Material_Ensenanza/Curso/` y léxico de `02_Diccionario/datos/`.

    python tools/owee_curso.py /ruta/al/repositorio/owee

El contenido es de Hector Martinez (CC BY-SA 4.0). No se edita a mano: se corrige en el repositorio de Owee y se regenera.
"""
import csv
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def niveles(repo: Path) -> list[dict]:
    out = []
    for n in range(4):
        texto = (repo / f"03_Material_Ensenanza/Curso/Owee_Curso_Nivel_{n}.md").read_text(encoding="utf-8")
        cabecera, *lecciones = re.split(r"^## (?=Lección )", texto, flags=re.M)
        titulo = re.match(r"# Nivel \d+ — (.+)", cabecera).group(1).strip()
        objetivo = next((l.strip() for l in cabecera.splitlines()[1:] if l.strip()), "")      # primera línea: «Objetivo: … Duración: …»
        objetivo = re.sub(r"^\*\*Objetivo:\*\*\s*", "", objetivo).replace("**", "")
        out.append({"n": n, "titulo": titulo, "objetivo": objetivo, "lecciones": []})
        for bloque in lecciones:
            enc, _, cuerpo = bloque.partition("\n")
            m = re.match(r"Lección (\d+\.\d+) — (.+)", enc.strip())
            out[-1]["lecciones"].append({"id": m.group(1), "titulo": m.group(2).strip(), "md": cuerpo.strip("\n")})
    return out


def lexico(repo: Path) -> dict[str, tuple[str, str]]:
    datos = {}
    for nombre in ("lexico.tsv", "lexico_ciencias.tsv"):
        with open(repo / "02_Diccionario/datos" / nombre, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                datos.setdefault(r["owee"].strip().lower(), (r["significado"].strip(), r["clase"].strip()))
    return datos


def main(repo: Path):
    niv, lex = niveles(repo), lexico(repo)
    lineas = ['"""Curso de Owee por niveles. Generado por tools/owee_curso.py desde https://github.com/oweeme/owee',
              '(Hector Martinez, CC BY-SA 4.0). No lo edites a mano: corrige en el repositorio de Owee y vuelve a generarlo."""',
              f"NIVELES = {niv!r}", "", f"LEXICO = {lex!r}", ""]
    (RAIZ / "owee_curso/datos.py").write_text("\n".join(lineas), encoding="utf-8")
    n_lec = sum(len(n["lecciones"]) for n in niv)
    print(f"{len(niv)} niveles, {n_lec} lecciones, {len(lex)} palabras de léxico")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
