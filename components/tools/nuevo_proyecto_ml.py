#!/usr/bin/env python3
"""Crea un proyecto de ML nuevo con la estructura estándar y el registro de versiones.

Uso: python nuevo_proyecto_ml.py <ruta> [--perfil "Estudio + informe"]
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import registro_ml  # noqa: E402

CARPETAS = ["data/raw", "data/processed", "src", "modelo V1", "registro", "reports", "experiments",
            "docs/journal", "temporal", "obsoleto"]
GITIGNORE = ("data/\ntemporal/\n*.xlsx\n*.xls\n*.pptx\n*.joblib\n*.pkl\n"
             "*.docx\n*.doc\n*.pdf\n*.csv\n*.parquet\n*.feather\n*.h5\n*.hdf5\n"
             "*.pt\n*.pth\n*.onnx\n*.ckpt\n*.safetensors\n"
             "*.png\n*.jpg\n*.jpeg\n*.zip\n"
             "__pycache__/\n.pytest_cache/\n.env\n"
             # Excepción: los ficheros de prueba de los tests sí van a git, aunque sean .csv,
             # .xlsx… (va al final para que ninguna regla posterior la vuelva a ignorar).
             "!tests/fixtures/**\n")
README = """# {nombre}

Perfil: **{perfil}** (ver la skill `mle-workflow`).

| Carpeta | Qué contiene |
|---|---|
| `data/raw/` | Datos de origen tal como llegan. Solo lectura: se corrigen en código, nunca a mano. |
| `data/processed/` | Datos limpios generados por el código. |
| `src/` | Código. `registro_ml.py` registra cada versión. |
| `modelo VNN/` | Todo lo de esa versión (modelo, trazabilidad, justificación, informe, ppt, entrega). Solo las 2 últimas a la vista; las anteriores van a obsoleto/. |
| `registro/` | Ficha de cada versión: parámetros, métricas y huellas digitales de los datos (huella digital o SHA-256: un código que cambia si cambia un solo byte del fichero). |
| `reports/` | Documentos generales del proyecto (no de una versión concreta). |
| `experiments/` | Pruebas exploratorias. |
| `docs/journal/` | Resumen de cada sesión de trabajo. |
| `temporal/` | Copias de prueba (fuera de git). |
| `obsoleto/` | Lo superado. |

Regla de versiones: cada versión vive entera en su propia carpeta `modelo VNN/` (modelo,
memoria de trazabilidad, justificación, informe, ppt y entrega al cliente). En la raíz del
proyecto solo se ven las 2 últimas versiones; al nacer una tercera, la más antigua de las
visibles se mueve a `obsoleto/`.

La versión vigente y el historial están en `VERSIONES.md` (se genera solo).
Comparar versiones: `python src/registro_ml.py comparar V1 V2`.
"""


def crear(ruta: Path, perfil: str) -> None:
    ruta = Path(ruta)
    if ruta.exists() and any(ruta.iterdir()):
        raise SystemExit(f"{ruta} no está vacía: no creo nada.")
    for carpeta in CARPETAS:
        (ruta / carpeta).mkdir(parents=True, exist_ok=True)
    shutil.copy2(AQUI / "registro_ml.py", ruta / "src" / "registro_ml.py")
    (ruta / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (ruta / "README.md").write_text(README.format(nombre=ruta.name, perfil=perfil), encoding="utf-8")
    registro_ml.regenerar(ruta)
    if shutil.which("git"):
        subprocess.run(["git", "init", "-q", "-b", "main", str(ruta)], check=False)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("ruta")
    p.add_argument("--perfil", default="Estudio + informe")
    args = p.parse_args(argv)
    crear(Path(args.ruta), args.perfil)
    print(f"Proyecto creado en {args.ruta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
