"""Busca en el código las llamadas a t() y tn() para saber qué textos hay que traducir.

    python -m i18n.extraer            # lista los textos que faltan en cada idioma
"""
import ast
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CARPETAS = ("ui", "engine", "database", "parsers", "main.py")
VARIABLE = re.compile(r"\{([A-Za-z_]\w*)")


def _llamadas(ruta: Path):
    arbol = ast.parse(ruta.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Name) and nodo.func.id in ("t", "tn", "marcar"):
            yield nodo


def extraer() -> tuple[dict[str, str], list[str]]:
    """Devuelve ({clave: 'archivo:línea'}, errores). Clave = texto español; en tn() la forma plural."""
    claves, errores = {}, []
    archivos = []
    for c in CARPETAS:
        p = RAIZ / c
        archivos += [p] if p.is_file() else sorted(p.rglob("*.py"))
    for f in archivos:
        for n in _llamadas(f):
            pos = 2 if n.func.id == "tn" else 0
            donde = f"{f.relative_to(RAIZ)}:{n.lineno}"
            arg = n.args[pos] if len(n.args) > pos else None
            if arg is None or not isinstance(arg, (ast.Constant, ast.JoinedStr, ast.BinOp)):
                continue   # t(x): x viene de una lista declarada con marcar()
            if isinstance(arg, (ast.JoinedStr, ast.BinOp)) or (isinstance(arg, ast.Constant) and not isinstance(arg.value, str)):
                errores.append(f"{donde}: {n.func.id}() debe recibir un texto literal (no un f-string ni una suma)")
                continue
            claves.setdefault(n.args[pos].value, donde)
    return claves, errores


def sombras() -> list[str]:
    """Funciones que llaman a t()/tn() pero también usan `t` como variable propia (daría UnboundLocalError)."""
    malas = []
    archivos = [RAIZ / "main.py"] + [f for c in CARPETAS[:-1] for f in sorted((RAIZ / c).rglob("*.py"))]
    for f in archivos:
        for fn in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if not isinstance(fn, (ast.FunctionDef, ast.Lambda)):
                continue
            nombres = {a.arg for a in fn.args.args + fn.args.kwonlyargs}
            if isinstance(fn, ast.FunctionDef):
                for n in ast.walk(fn):
                    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                        nombres.add(n.id)
            if nombres & {"t", "tn"} and any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                                             and n.func.id in ("t", "tn") for n in ast.walk(fn)):
                malas.append(f"{f.relative_to(RAIZ)}:{fn.lineno}")
    return malas


def plurales() -> set[str]:
    """Claves usadas con tn() (su traducción debe ser una tupla de formas)."""
    out = set()
    for c in CARPETAS:
        p = RAIZ / c
        for f in ([p] if p.is_file() else sorted(p.rglob("*.py"))):
            for n in _llamadas(f):
                if n.func.id == "tn" and len(n.args) > 2 and isinstance(n.args[2], ast.Constant):
                    out.add(n.args[2].value)
    return out


def variables(texto: str) -> set[str]:
    return set(VARIABLE.findall(texto))


if __name__ == "__main__":
    from i18n.catalogos import CATALOGOS
    claves, errores = extraer()
    print("\n".join(errores))
    for cod, cat in CATALOGOS.items():
        faltan = [k for k in claves if k not in cat]
        print(f"[{cod}] {len(claves) - len(faltan)}/{len(claves)} traducidos")
        for k in faltan:
            print("   falta:", k[:90], "→", claves[k])
    sys.exit(1 if errores else 0)
