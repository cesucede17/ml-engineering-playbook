#!/usr/bin/env python3
"""registro_ml: registro ligero de versiones de modelos y resultados.

Toma ideas de MLflow (guardar parámetros, métricas y resultado de cada versión) y de DVC
(huella digital de cada fichero de datos, entradas y salidas declaradas, comparar versiones),
sin instalar nada: solo la biblioteca estándar de Python.

En código:
    with version("V3", proyecto=".", descripcion="...") as v:
        v.parametros(alpha=0.25)
        v.datos("data/raw/cliente/consumos.xlsx")
        ...cálculo...
        v.metricas(ahorro_kwh=120000)
        v.resultado("models/V3/resultado.xlsx")

En consola:
    python src/registro_ml.py verificar V3
    python src/registro_ml.py comparar V2 V3
    python src/registro_ml.py registrar V1 --descripcion "..." --datos ... --resultado ... --param k=v --metrica k=v --fecha AAAA-MM-DD
    python src/registro_ml.py vigente V3
    python src/registro_ml.py regenerar
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import re
import subprocess
import sys
from contextlib import contextmanager
from importlib import metadata
from pathlib import Path

FORMATO = 1
LIBRERIAS = ("pandas", "numpy", "scikit-learn", "scipy", "statsmodels", "openpyxl", "torch")


def huella(ruta) -> str:
    """Huella digital (SHA-256) del contenido de un fichero: cambia si cambia un solo byte."""
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _relativa(proyecto: Path, ruta) -> tuple[Path, str]:
    p = Path(ruta)
    p = (p if p.is_absolute() else proyecto / p).resolve()
    try:
        return p, p.relative_to(proyecto).as_posix()
    except ValueError:
        return p, p.as_posix()


def _codigo(proyecto: Path) -> str | None:
    try:
        r = subprocess.run(["git", "-C", str(proyecto), "rev-parse", "--short", "HEAD"],
                           capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return None
        sucio = subprocess.run(["git", "-C", str(proyecto), "status", "--porcelain", "--untracked-files=no"],
                               capture_output=True, text=True, timeout=5).stdout.strip()
        return r.stdout.strip() + ("+cambios_sin_commit" if sucio else "")
    except (OSError, subprocess.SubprocessError):
        return None


def _librerias() -> dict[str, str]:
    salida = {"python": platform.python_version()}
    for nombre in LIBRERIAS:
        try:
            salida[nombre] = metadata.version(nombre)
        except metadata.PackageNotFoundError:
            pass
    return salida


def _registro(proyecto: Path) -> Path:
    return Path(proyecto) / "registro"


def leer(proyecto, nombre: str) -> dict:
    return json.loads((_registro(Path(proyecto)) / f"{nombre}.json").read_text(encoding="utf-8"))


def _numero_version(nombre: str) -> int | None:
    m = re.search(r"\d+", nombre)
    return int(m.group()) if m else None


def _clave_version(v: dict) -> tuple:
    """Orden cronológico: por fecha y, a igualdad de fecha, por el número de versión
    (V2 antes que V10; si no hay número, se ordena por el nombre)."""
    numero = _numero_version(v.get("version", ""))
    if numero is not None:
        return (v.get("fecha", ""), 0, numero, "")
    return (v.get("fecha", ""), 1, 0, v.get("version", ""))


def versiones(proyecto) -> list[dict]:
    carpeta = _registro(Path(proyecto))
    if not carpeta.is_dir():
        return []
    todas = [json.loads(f.read_text(encoding="utf-8")) for f in carpeta.glob("*.json")]
    return sorted(todas, key=_clave_version)


def _params_yaml(parametros: dict) -> str:
    return "".join(f"{k}: {json.dumps(v, ensure_ascii=False)}\n" for k, v in parametros.items())


def regenerar(proyecto) -> None:
    """Rehace VERSIONES.md a partir de registro/ (vista generada: no se edita a mano)."""
    proyecto = Path(proyecto)
    fichero_vigente = _registro(proyecto) / "vigente.txt"
    vigente = fichero_vigente.read_text(encoding="utf-8").strip() if fichero_vigente.exists() else "(sin marcar)"
    lineas = [f"# Versiones de {proyecto.resolve().name}", "",
              "<!-- Generado por registro_ml.py a partir de registro/. No editar a mano. -->", "",
              f"**Vigente:** {vigente}", "",
              "| Versión | Fecha | Descripción | Métricas | Datos | Código |",
              "|---|---|---|---|---|---|"]
    for v in versiones(proyecto):
        marca = " ✅" if v["version"] == vigente else ""
        metricas = ", ".join(f"{k}={val}" for k, val in v["metricas"].items()).replace("|", "/") or "—"
        descripcion = (v.get("descripcion") or "—").replace("|", "/")
        lineas.append(f"| {v['version']}{marca} | {v['fecha'][:10]} | {descripcion} | {metricas} | "
                      f"{len(v['datos'])} ficheros | {v.get('codigo') or '—'} |")
    (proyecto / "VERSIONES.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def _avisos(proyecto: Path, nombre: str, fecha: str, datos: dict[str, str]) -> list[str]:
    """Avisa si los datos cambiaron respecto al predecesor cronológico (fecha, número de
    versión), no respecto a la última versión registrada: un registro a posteriori con una
    fecha antigua no debe avisar contra versiones posteriores en el tiempo."""
    propia = _clave_version({"version": nombre, "fecha": fecha})
    anteriores = [v for v in versiones(proyecto) if v["version"] != nombre and _clave_version(v) < propia]
    if not anteriores:
        return []
    previa = max(anteriores, key=_clave_version)
    return [f"{ruta}: los datos han cambiado respecto a {previa['version']}"
            for ruta, h in datos.items() if previa.get("datos", {}).get(ruta, h) != h]


def _guardar(proyecto: Path, registro: dict, sobrescribir: bool = False) -> None:
    carpeta = _registro(proyecto)
    carpeta.mkdir(parents=True, exist_ok=True)
    nombre = registro["version"]
    if not sobrescribir and (carpeta / f"{nombre}.json").exists():
        raise FileExistsError(
            f"{nombre}: ya hay una versión registrada (registro/{nombre}.json); "
            f"usa sobrescribir=True (o --sobrescribir en la CLI) si quieres reemplazarla")
    (carpeta / f"{nombre}.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    (carpeta / f"{nombre}.params.yaml").write_text(_params_yaml(registro["parametros"]), encoding="utf-8")
    regenerar(proyecto)


class Version:
    def __init__(self, nombre: str, proyecto: Path, descripcion: str):
        self.nombre, self.proyecto, self.descripcion = nombre, proyecto, descripcion
        self._datos: dict[str, str] = {}
        self._resultados: list[tuple[Path, str]] = []
        self._parametros: dict = {}
        self._metricas: dict = {}

    def datos(self, *rutas) -> None:
        """Declara ficheros de entrada y guarda ya su huella (como las dependencias de DVC)."""
        for ruta in rutas:
            p, rel = _relativa(self.proyecto, ruta)
            self._datos[rel] = huella(p)

    def parametros(self, **valores) -> None:
        self._parametros.update(valores)

    def metricas(self, **valores) -> None:
        self._metricas.update(valores)

    def resultado(self, *rutas) -> None:
        """Declara ficheros de salida; su huella se calcula al cerrar la versión."""
        self._resultados += [_relativa(self.proyecto, ruta) for ruta in rutas]

    def cerrar(self, fecha: str | None = None, a_posteriori: bool = False,
               sobrescribir: bool = False) -> dict:
        fecha_final = fecha or dt.datetime.now().isoformat(timespec="seconds")
        registro = {
            "formato": FORMATO,
            "version": self.nombre,
            "fecha": fecha_final,
            "descripcion": self.descripcion,
            "parametros": self._parametros,
            "metricas": self._metricas,
            "datos": self._datos,
            "resultados": {rel: huella(p) for p, rel in self._resultados},
            "codigo": "registrado a posteriori" if a_posteriori else _codigo(self.proyecto),
            "librerias": {} if a_posteriori else _librerias(),
            "avisos": _avisos(self.proyecto, self.nombre, fecha_final, self._datos),
        }
        _guardar(self.proyecto, registro, sobrescribir=sobrescribir)
        for aviso in registro["avisos"]:
            print(f"AVISO: {aviso}", file=sys.stderr)
        return registro


@contextmanager
def version(nombre: str, proyecto=".", descripcion: str = "", sobrescribir: bool = False):
    """Registra una versión si el bloque termina sin errores; si falla, no registra nada.
    Si ya existe un registro de `nombre`, falla con FileExistsError salvo que se pase
    `sobrescribir=True`."""
    v = Version(nombre, Path(proyecto).resolve(), descripcion)
    yield v
    v.cerrar(sobrescribir=sobrescribir)


def registrar(proyecto, nombre: str, descripcion: str, datos, resultados, parametros: dict,
              metricas: dict, fecha: str | None = None, sobrescribir: bool = False) -> dict:
    """Registra a posteriori una versión que ya existía (sin commit ni librerías). Si ya hay
    un registro de `nombre`, falla con FileExistsError salvo que se pase `sobrescribir=True`."""
    v = Version(nombre, Path(proyecto).resolve(), descripcion)
    v.datos(*datos)
    v.resultado(*resultados)
    v.parametros(**parametros)
    v.metricas(**metricas)
    return v.cerrar(fecha=fecha, a_posteriori=True, sobrescribir=sobrescribir)


def verificar(proyecto, nombre: str) -> list[tuple[str, str]]:
    proyecto = Path(proyecto).resolve()
    reg = leer(proyecto, nombre)
    estado = []
    for ruta, h in {**reg["datos"], **reg["resultados"]}.items():
        p, _ = _relativa(proyecto, ruta)
        if not p.exists():
            estado.append((ruta, "FALTA"))
        elif huella(p) != h:
            estado.append((ruta, "CAMBIADO"))
        else:
            estado.append((ruta, "OK"))
    return estado


def comparar(proyecto, a: str, b: str) -> list[str]:
    ra, rb = leer(proyecto, a), leer(proyecto, b)
    lineas = [f"{'':26}{a:>18}{b:>18}"]
    for titulo, clave in (("Parámetros", "parametros"), ("Métricas", "metricas")):
        lineas.append(titulo)
        for k in sorted(set(ra[clave]) | set(rb[clave])):
            va, vb = ra[clave].get(k, "—"), rb[clave].get(k, "—")
            lineas.append(f"  {k:24}{str(va):>18}{str(vb):>18}{'' if va == vb else '  *'}")
    lineas.append("Datos")
    da, db = ra["datos"], rb["datos"]
    cambios = [f"  cambiado: {x}" for x in sorted(set(da) & set(db)) if da[x] != db[x]]
    cambios += [f"  solo en {a}: {x}" for x in sorted(set(da) - set(db))]
    cambios += [f"  solo en {b}: {x}" for x in sorted(set(db) - set(da))]
    return lineas + (cambios or ["  (mismos datos)"])


def marcar_vigente(proyecto, nombre: str) -> None:
    proyecto = Path(proyecto)
    if not (_registro(proyecto) / f"{nombre}.json").exists():
        raise FileNotFoundError(f"No hay registro de {nombre}")
    (_registro(proyecto) / "vigente.txt").write_text(nombre + "\n", encoding="utf-8")
    regenerar(proyecto)


def _clave_valor(textos: list[str]) -> dict:
    salida = {}
    for texto in textos:
        clave, _, valor = texto.partition("=")
        try:
            salida[clave] = json.loads(valor)
        except json.JSONDecodeError:
            salida[clave] = valor
    return salida


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Registro ligero de versiones de modelos.")
    p.add_argument("--proyecto", default=".")
    sub = p.add_subparsers(dest="orden", required=True)
    sub.add_parser("verificar").add_argument("version")
    c = sub.add_parser("comparar")
    c.add_argument("a")
    c.add_argument("b")
    g = sub.add_parser("registrar")
    g.add_argument("version")
    g.add_argument("--descripcion", default="")
    g.add_argument("--datos", nargs="*", default=[])
    g.add_argument("--resultado", nargs="*", default=[])
    g.add_argument("--param", nargs="*", default=[])
    g.add_argument("--metrica", nargs="*", default=[])
    g.add_argument("--fecha")
    g.add_argument("--sobrescribir", action="store_true",
                   help="reemplaza el registro de esta versión si ya existe")
    sub.add_parser("vigente").add_argument("version")
    sub.add_parser("regenerar")
    args = p.parse_args(argv)
    proyecto = Path(args.proyecto).resolve()
    if args.orden == "verificar":
        estado = verificar(proyecto, args.version)
        for ruta, e in estado:
            print(f"{e:9} {ruta}")
        return 0 if all(e == "OK" for _, e in estado) else 1
    if args.orden == "comparar":
        print("\n".join(comparar(proyecto, args.a, args.b)))
    elif args.orden == "registrar":
        try:
            registrar(proyecto, args.version, args.descripcion, args.datos, args.resultado,
                      _clave_valor(args.param), _clave_valor(args.metrica), args.fecha,
                      sobrescribir=args.sobrescribir)
        except FileExistsError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"{args.version} registrada")
    elif args.orden == "vigente":
        marcar_vigente(proyecto, args.version)
        print(f"{args.version} marcada como vigente")
    else:
        regenerar(proyecto)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
