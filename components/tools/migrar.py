#!/usr/bin/env python3
"""Mueve ficheros de un proyecto según un plan y comprueba con huellas digitales que no se pierde nada.

plan.json: {"movimientos": [{"de": "ruta/actual", "a": "ruta/nueva"}, ...], "intocables": ["modelo V4", ...],
            "solo_anadir": ["modelo V3", ...]}
Intocables: no se mueve nada hacia ni desde ellos. Solo añadir (opcional): se puede mover algo
hacia dentro, pero lo que ya contienen sigue en la misma ruta y con la misma huella.
Sin --aplicar solo simula. Con --aplicar: inventario antes → mover → inventario después → comprobar;
si algo falla, deshace los movimientos.

AVISO: cierra Excel y el Explorador de archivos en la carpeta del proyecto antes de usar
--aplicar. Un fichero abierto impide moverlo y puede dejar la migración a medias.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

AVISO_CIERRE = ("Cierra Excel y el Explorador de archivos en la carpeta del proyecto antes de "
                "usar --aplicar: un fichero abierto impide moverlo y puede dejar la migración a medias.")

# .git, __pycache__ y .pytest_cache se excluyen en cualquier nivel del árbol.
EXCLUIR_SIEMPRE = {".git", "__pycache__", ".pytest_cache"}

_PATRON_UNIDAD = re.compile(r"^[A-Za-z]:")
# Nombre corto 8.3 de Windows (p. ej. «MODELO~2»): apunta a la misma carpeta que el nombre largo
# y burlaría las comprobaciones de intocables y «solo añadir», que comparan nombres.
_PATRON_NOMBRE_CORTO = re.compile(r"~\d")


class EstadoNoRestauradoError(OSError):
    """El deshacer no ha conseguido dejar el proyecto exactamente como estaba antes de aplicar."""


def _normalizar_ruta(ruta: str) -> str:
    """Normaliza una ruta relativa del plan: barra invertida -> barra, quita «./», colapsa
    barras repetidas. Lanza ValueError si la ruta es absoluta, usa «..», tiene una parte
    vacía o una parte termina en punto o en espacio (problemático en Windows)."""
    original = ruta
    r = ruta.replace("\\", "/")
    if _PATRON_UNIDAD.match(r) or r.startswith("/"):
        raise ValueError(f"{original}: ruta absoluta o con letra de unidad, no permitida")
    r = re.sub(r"/+", "/", r)
    partes: list[str] = []
    for parte in r.split("/"):
        if parte == ".":
            continue
        if parte == "":
            raise ValueError(f"{original}: contiene una parte vacía")
        if parte == "..":
            raise ValueError(f"{original}: no se permite «..» en la ruta")
        if parte.endswith(".") or parte.endswith(" "):
            raise ValueError(f"{original}: «{parte}» no puede terminar en punto o espacio")
        if _PATRON_NOMBRE_CORTO.search(parte):
            raise ValueError(f"{original}: «{parte}» parece un nombre corto 8.3 de Windows; "
                             f"usa el nombre largo, no el nombre corto 8.3")
        partes.append(parte)
    if not partes:
        raise ValueError(f"{original}: ruta vacía")
    return "/".join(partes)


def _huella(ruta: Path) -> str:
    h = hashlib.sha256()
    with open(ruta, "rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _excluido(partes: tuple[str, ...], informes_partes: tuple[str, ...] | None) -> bool:
    if EXCLUIR_SIEMPRE & set(partes):
        return True
    # "temporal" solo se excluye en el nivel superior del proyecto (ahí es donde este
    # programa guarda sus propios informes), sin distinguir mayúsculas.
    if partes and partes[0].lower() == "temporal":
        return True
    # La carpeta de informes de esta ejecución, si cae dentro del proyecto con otro nombre.
    if informes_partes and partes[: len(informes_partes)] == informes_partes:
        return True
    return False


def inventario(proyecto: Path, informes: Path | None = None) -> dict[str, str]:
    proyecto = Path(proyecto)
    informes_partes = None
    if informes is not None:
        try:
            informes_partes = Path(informes).resolve().relative_to(proyecto.resolve()).parts
        except ValueError:
            informes_partes = None
    salida = {}
    for f in sorted(proyecto.rglob("*")):
        if not f.is_file():
            continue
        partes = f.relative_to(proyecto).parts
        if _excluido(partes, informes_partes):
            continue
        salida[f.relative_to(proyecto).as_posix()] = _huella(f)
    return salida


def _dentro(ruta: str, carpeta: str) -> bool:
    ruta, carpeta = ruta.strip("/").lower(), carpeta.strip("/").lower()
    return ruta == carpeta or ruta.startswith(carpeta + "/")


def _claves_comparables(inventario_: dict[str, str]) -> dict[str, str]:
    """Las claves (rutas) de un inventario, listas para comparar dos inventarios entre sí.
    Solo se pliegan a minúsculas en un sistema de ficheros insensible a mayúsculas (Windows):
    ahí, dos rutas que solo difieren en mayúsculas SON el mismo fichero, así que comparar en
    minúsculas evita un falso "ha cambiado" tras un simple renombrado de mayúsculas. En Linux
    (sensible a mayúsculas) hay que comparar la ruta exacta: si no, dos ficheros reales que
    solo difieren en mayúsculas colapsarían en una sola clave y un fichero perdido (p. ej.
    sobrescrito por un renombrado que colisiona) pasaría desapercibido."""
    if os.name == "nt":
        return {k.lower(): v for k, v in inventario_.items()}
    return dict(inventario_)


def _existe_virtual(proyecto: Path, ruta: str, previos: list[tuple[str, str]]) -> bool:
    """¿Existe `ruta` justo antes de aplicar el siguiente movimiento, simulando en orden los
    movimientos `previos` (ya "aplicados" virtualmente)? Así, un `de` o un `a` que se apoye en
    el resultado de un movimiento anterior del mismo plan (una cadena, p. ej. "a"->"b" y luego
    "b/x"->"c") se valida correctamente, y uno que ya se movió fuera de su sitio (p. ej.
    "analisis"->"src" y luego "analisis/x"->...) se detecta como inexistente."""
    for de_i, a_i in reversed(previos):
        if _dentro(ruta, a_i):
            return True
        if _dentro(ruta, de_i):
            return False
    return (proyecto / ruta).exists()


def _mismo_fichero(p1: Path, p2: Path) -> bool:
    """¿p1 y p2 son, de verdad, el mismo fichero/carpeta ya existente? Se decide SIEMPRE con
    os.path.samefile, nunca comparando cadenas en minúsculas: en un sistema de ficheros
    sensible a mayúsculas (Linux), "cliente.xlsx" y "Cliente.xlsx" pueden ser dos ficheros
    DISTINTOS que existen los dos a la vez, y tratarlos como "el mismo fichero" por el simple
    hecho de que coinciden en minúsculas perdería el que ya hubiera en el destino (ver
    _renombrado_de_si_mismo, que es quien decide si un simple cambio de mayúsculas sin
    colisión cuenta como renombrado de sí mismo)."""
    try:
        return p1.exists() and p2.exists() and os.path.samefile(p1, p2)
    except OSError:
        return False


def _renombrado_de_si_mismo(proyecto: Path, de: str, a: str, previos: list[tuple[str, str]]) -> bool:
    """¿Cuenta `de -> a` como un renombrado «de sí mismo» (no un choque, no «mover dentro de
    sí misma»)? Dos casos:
    - `de` y `a` son, de verdad, el mismo fichero/carpeta ya existente (_mismo_fichero): el
      caso normal en Windows, donde un simple cambio de mayúsculas "existe" igual que el
      original.
    - `de` y `a` son el mismo nombre salvo mayúsculas/minúsculas Y el destino NO existe
      todavía -ni físicamente ni de forma virtual en la cadena de movimientos previos del
      plan-: un simple renombrado de mayúsculas en un sistema de ficheros que SÍ las
      distingue (Linux).
    Si `de` y `a` solo difieren en mayúsculas pero el destino YA EXISTE como un fichero
    propio (dos ficheros reales que solo difieren en mayúsculas, posible en Linux), esto
    devuelve False: no es un renombrado de sí mismo, es un choque real, y validar() debe
    rechazarlo con «el destino ya existe», igual que cualquier otro choque."""
    if _mismo_fichero(proyecto / de, proyecto / a):
        return True
    return de.lower() == a.lower() and de != a and not _existe_virtual(proyecto, a, previos)


def validar(proyecto: Path, plan: dict) -> list[str]:
    proyecto = Path(proyecto)
    errores: list[str] = []
    destinos: set[str] = set()

    intocables: list[str] = []
    for intocable_crudo in plan.get("intocables", []):
        try:
            intocable = _normalizar_ruta(intocable_crudo)
        except ValueError as exc:
            errores.append(str(exc))
            continue
        intocables.append(intocable)
        if not (proyecto / intocable).exists():
            errores.append(f"{intocable}: el intocable no existe")

    # Carpetas «solo añadir»: se puede mover algo hacia dentro, pero nada de lo que ya
    # contienen puede salir, moverse dentro de ellas, cambiar ni borrarse.
    solo_anadir: list[str] = []
    for sa_crudo in plan.get("solo_anadir", []):
        try:
            sa = _normalizar_ruta(sa_crudo)
        except ValueError as exc:
            errores.append(str(exc))
            continue
        solo_anadir.append(sa)
        if not (proyecto / sa).is_dir():
            errores.append(f"{sa}: la carpeta «solo añadir» no existe")
        for intocable in intocables:
            if sa.lower() == intocable.lower():
                errores.append(f"{sa}: no puede ser a la vez intocable y «solo añadir»")

    previos: list[tuple[str, str]] = []
    for indice, mov in enumerate(plan["movimientos"]):
        if "de" not in mov or "a" not in mov:
            errores.append(f"movimiento #{indice + 1}: falta «de» o «a» en el plan")
            continue
        try:
            de = _normalizar_ruta(mov["de"])
        except ValueError as exc:
            errores.append(str(exc))
            continue
        try:
            a = _normalizar_ruta(mov["a"])
        except ValueError as exc:
            errores.append(str(exc))
            continue

        es_renombrado_de_si_mismo = _renombrado_de_si_mismo(proyecto, de, a, previos)

        if not _existe_virtual(proyecto, de, previos):
            errores.append(f"{de}: el origen no existe")
        if not es_renombrado_de_si_mismo and _existe_virtual(proyecto, a, previos):
            errores.append(f"{a}: el destino ya existe")
        if a.lower() in destinos:
            errores.append(f"{a}: destino repetido en el plan")
        destinos.add(a.lower())

        for intocable in intocables:
            # de/a dentro del intocable, o el intocable dentro de de (mover un padre del
            # intocable se lo llevaría también a él).
            if _dentro(de, intocable) or _dentro(a, intocable) or _dentro(intocable, de):
                errores.append(f"{de} -> {a}: afecta al intocable «{intocable}»")

        for sa in solo_anadir:
            # Un «a» dentro está permitido (el destino en sí no puede existir ya, eso ya se
            # comprueba arriba); un «de» dentro, o un «de» que sea padre de la carpeta, no.
            if _dentro(de, sa) or _dentro(sa, de):
                errores.append(f"{de} -> {a}: saca o mueve algo de la carpeta solo añadir «{sa}»")

        if not es_renombrado_de_si_mismo and _dentro(a, de):
            errores.append(f"{de} -> {a}: no se puede mover una carpeta dentro de sí misma")

        for de_i, a_i in previos:
            if _dentro(a, de_i):
                errores.append(f"{de} -> {a}: el destino cae dentro del origen de un movimiento "
                                f"anterior («{de_i} -> {a_i}»)")

        previos.append((de, a))

    # Un destino no puede caer dentro del árbol de otro destino del mismo plan (en cualquier
    # orden): el primero convertiría esa ruta en un fichero y el segundo no podría crear ahí
    # una carpeta, dejando la migración a medias.
    rutas_a = [a for _, a in previos]
    for i, a1 in enumerate(rutas_a):
        for j, a2 in enumerate(rutas_a):
            if i != j and _dentro(a2, a1):
                errores.append(f"{a2}: el destino cae dentro de otro destino del plan («{a1}»)")
    return errores


def _aplicar_mapeo(antes: dict[str, str], movimientos) -> dict[str, str]:
    """Aplica el mapeo de movimientos (de -> a) a las claves de `antes`, también para
    movimientos de carpetas enteras (todo lo que cuelga de «de» pasa a colgar de «a»)."""
    esperado = dict(antes)
    for mov in movimientos:
        de, a = mov["de"], mov["a"]
        afectados = [k for k in esperado if _dentro(k, de)]
        for k in afectados:
            sufijo = k[len(de):]
            esperado[a + sufijo] = esperado.pop(k)
    return esperado


def comprobar(antes: dict[str, str], despues: dict[str, str], intocables: list[str],
              movimientos=(), solo_anadir=()) -> list[str]:
    problemas = []
    if Counter(antes.values()) != Counter(despues.values()):
        problemas.append("el conjunto de huellas ha cambiado: se ha perdido o modificado algún fichero")
    for intocable in intocables:
        a = {r: h for r, h in antes.items() if _dentro(r, intocable)}
        d = {r: h for r, h in despues.items() if _dentro(r, intocable)}
        if a != d:
            problemas.append(f"el intocable «{intocable}» ha cambiado")
    for sa in solo_anadir:
        # Cada fichero que ya estaba dentro debe seguir en la misma ruta con la misma huella;
        # los ficheros nuevos se permiten.
        alterados = sorted(r for r, h in antes.items() if _dentro(r, sa) and despues.get(r) != h)
        if alterados:
            problemas.append(f"la carpeta solo añadir «{sa}» ha cambiado: se ha movido, modificado "
                              f"o borrado {', '.join(alterados)}")
    if movimientos:
        # Además del multiconjunto de huellas (que no distingue QUÉ fichero ha ido a cada
        # sitio cuando dos comparten huella), se exige que el mapeo de rutas del plan,
        # aplicado a `antes`, coincida EXACTAMENTE con `despues` (ver _claves_comparables:
        # sin distinguir mayúsculas solo en Windows).
        esperado = _aplicar_mapeo(antes, movimientos)
        esperado_cf = _claves_comparables(esperado)
        despues_cf = _claves_comparables(despues)
        if esperado_cf != despues_cf:
            problemas.append("el resultado no coincide exactamente con lo que el plan preveía: "
                              "algún fichero ha terminado en un sitio distinto al previsto, aunque "
                              "las huellas en conjunto cuadren")
    return problemas


def _directorios_a_crear(ruta: Path, proyecto: Path) -> list[Path]:
    """Carpetas que `ruta.mkdir(parents=True)` crearía de nuevas (de arriba hacia abajo),
    para poder deshacerlas después si hace falta."""
    faltantes = []
    actual = ruta
    while actual != proyecto and not actual.exists():
        faltantes.append(actual)
        siguiente = actual.parent
        if siguiente == actual:
            break
        actual = siguiente
    faltantes.reverse()
    return faltantes


def _deshacer(proyecto: Path, hechos: list[dict], creadas: list[Path] | None = None) -> list[str]:
    """Deshace los movimientos de `hechos` en orden inverso. No mueve nunca si el origen
    original ya existe de nuevo (salvo que sea una carpeta vacía creada por la propia
    herramienta al abrir camino, en cuyo caso se borra y se sigue). Cada paso que no se puede
    deshacer se anota en la lista devuelta: nunca se salta en silencio. Cada paso va envuelto
    en su propio try/except: si uno falla (p. ej. un fichero bloqueado, WinError 5), se anota
    y se sigue con el resto — un fallo aislado no debe abortar el deshacer de todo lo demás."""
    creadas_set = set(creadas or [])
    problemas: list[str] = []
    for mov in reversed(hechos):
        origen = proyecto / mov["de"]
        destino = proyecto / mov["a"]
        try:
            if not destino.exists():
                problemas.append(f"{mov['de']} <- {mov['a']}: no se pudo deshacer, el destino ya no está ahí")
                continue
            if origen.exists():
                if origen in creadas_set and origen.is_dir() and not any(origen.iterdir()):
                    origen.rmdir()
                else:
                    problemas.append(f"{mov['de']} <- {mov['a']}: no se pudo deshacer, el origen ya existe")
                    continue
            origen.parent.mkdir(parents=True, exist_ok=True)
            os.rename(str(destino), str(origen))
        except OSError as exc:
            problemas.append(f"{mov['de']} <- {mov['a']}: no se pudo deshacer, {exc}")
    return problemas


def _borrar_vacias(creadas: list[Path]) -> None:
    for carpeta in sorted(set(creadas), key=lambda p: len(p.parts), reverse=True):
        try:
            if carpeta.is_dir() and not any(carpeta.iterdir()):
                carpeta.rmdir()
        except OSError:
            pass


def _deshacer_y_verificar(proyecto: Path, informes: Path, antes: dict[str, str],
                           hechos: list[dict], creadas: list[Path]) -> tuple[list[str], bool]:
    """Deshace y comprueba que el proyecto ha quedado EXACTAMENTE como `antes` (ruta -> huella;
    ver _claves_comparables: sin distinguir mayúsculas solo en Windows, porque en Linux dos
    rutas que solo difieren en mayúsculas pueden ser dos ficheros reales distintos y
    colapsarlas en una sola clave ocultaría que uno de los dos se ha perdido). Escribe
    `inventario_tras_deshacer.json` para que quede constancia. Si todo ha quedado restaurado,
    limpia las carpetas vacías que creó la herramienta. Nunca deja escapar una excepción: si
    ni siquiera se puede recalcular el inventario para comprobarlo, se trata como «no
    restaurado» en vez de reventar y perder el aviso de ESTADO NO RESTAURADO."""
    problemas = _deshacer(proyecto, hechos, creadas)
    try:
        tras = inventario(proyecto, informes)
        (informes / "inventario_tras_deshacer.json").write_text(
            json.dumps(tras, indent=1, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        problemas.append(f"no se pudo comprobar el estado tras deshacer: {exc}")
        return problemas, False
    antes_cf = _claves_comparables(antes)
    tras_cf = _claves_comparables(tras)
    restaurado = antes_cf == tras_cf
    if restaurado:
        _borrar_vacias(creadas)
    return problemas, restaurado


def aplicar(proyecto: Path, plan: dict, informes: Path) -> int:
    proyecto = Path(proyecto)
    errores = validar(proyecto, plan)
    if errores:
        print("\n".join(errores), file=sys.stderr)
        return 1
    intocables = [_normalizar_ruta(i) for i in plan.get("intocables", [])]
    solo_anadir = [_normalizar_ruta(s) for s in plan.get("solo_anadir", [])]
    movimientos = [{"de": _normalizar_ruta(mov["de"]), "a": _normalizar_ruta(mov["a"])}
                   for mov in plan["movimientos"]]

    informes = Path(informes)
    informes.mkdir(parents=True, exist_ok=True)
    antes = inventario(proyecto, informes)
    (informes / "inventario_antes.json").write_text(
        json.dumps(antes, indent=1, ensure_ascii=False), encoding="utf-8")
    (informes / "plan.json").write_text(json.dumps(plan, indent=1, ensure_ascii=False), encoding="utf-8")

    hechos: list[dict] = []
    creadas: list[Path] = []
    try:
        with open(informes / "movimientos.log", "a", encoding="utf-8") as log:
            for mov in movimientos:
                origen = proyecto / mov["de"]
                destino = proyecto / mov["a"]
                log.write(f"{dt.datetime.now().isoformat(timespec='seconds')} ANTES    {mov['de']} -> {mov['a']}\n")
                log.flush()
                creadas.extend(_directorios_a_crear(destino.parent, proyecto))
                destino.parent.mkdir(parents=True, exist_ok=True)
                os.rename(str(origen), str(destino))
                hechos.append(mov)
                log.write(f"{dt.datetime.now().isoformat(timespec='seconds')} DESPUÉS  {mov['de']} -> {mov['a']}\n")
                log.flush()
        # El inventario de después y su escritura están dentro de la zona protegida: si
        # fallan (disco lleno, fichero bloqueado al leer, etc.), también se deshace.
        despues = inventario(proyecto, informes)
        (informes / "inventario_despues.json").write_text(
            json.dumps(despues, indent=1, ensure_ascii=False), encoding="utf-8")
        problemas = comprobar(antes, despues, intocables, movimientos, solo_anadir)
    except BaseException as exc:
        # BaseException (no solo Exception): KeyboardInterrupt (Ctrl+C) y SystemExit también
        # deben disparar el deshacer. El inventario de después puede tardar minutos con
        # proyectos grandes, y es el momento típico en que el usuario pulsa Ctrl+C; sin esto,
        # la migración quedaría a medias, sin comprobar y sin el aviso de ESTADO NO RESTAURADO.
        problemas_deshacer, restaurado = _deshacer_y_verificar(proyecto, informes, antes, hechos, creadas)
        if not restaurado:
            detalle = "; ".join(problemas_deshacer) if problemas_deshacer else "sin más detalle"
            raise EstadoNoRestauradoError(
                f"ESTADO NO RESTAURADO: usa la copia de seguridad. ({detalle})") from exc
        if problemas_deshacer:
            print("\n".join(problemas_deshacer), file=sys.stderr)
        print("Estado restaurado exactamente.", file=sys.stderr)
        raise
    if problemas:
        problemas_deshacer, restaurado = _deshacer_y_verificar(proyecto, informes, antes, hechos, creadas)
        mensaje = "\n".join(problemas)
        if problemas_deshacer:
            mensaje += "\n" + "\n".join(problemas_deshacer)
        if not restaurado:
            print(mensaje + "\nESTADO NO RESTAURADO: usa la copia de seguridad.", file=sys.stderr)
            return 2
        print(mensaje + "\nEstado restaurado exactamente.", file=sys.stderr)
        return 1
    print(f"OK: {len(hechos)} movimientos, {len(despues)} ficheros con las mismas huellas.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=f"{__doc__}")
    p.add_argument("--proyecto", required=True)
    p.add_argument("--plan", required=True)
    p.add_argument("--aplicar", action="store_true")
    p.add_argument("--informes")
    args = p.parse_args(argv)
    proyecto = Path(args.proyecto).resolve()
    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    if not args.aplicar:
        errores = validar(proyecto, plan)
        print("SIMULACIÓN (no se mueve nada)")
        print(AVISO_CIERRE)
        for mov in plan["movimientos"]:
            print(f"  {mov.get('de', '?')}  ->  {mov.get('a', '?')}")
        print("\n".join(errores) if errores else "Plan válido.")
        return 1 if errores else 0
    sello = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    informes = Path(args.informes) if args.informes else proyecto / "temporal" / f"migracion_{sello}"
    try:
        return aplicar(proyecto, plan, informes)
    except EstadoNoRestauradoError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrumpido: estado restaurado, no se ha aplicado nada.", file=sys.stderr)
        return 130
    except OSError as exc:
        print(f"Fallo al aplicar: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Fallo al aplicar: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    sys.exit(main())
