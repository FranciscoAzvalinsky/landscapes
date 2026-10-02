#!/usr/bin/env python3
"""
Mantiene tus mods organizados en subcarpetas (biblioteca) y genera una carpeta `mods`
plana, que es la unica que Fabric lee.

Estructura esperada (dentro de --base, por defecto tu .minecraft):
  mods_biblioteca/
      terrain/ dimension/ libs/ ...           <- tus subcarpetas (puedes anidar mas)
      fabric-api-....jar                       <- los .jar sueltos tambien cuentan
  mods/                                        <- la genera este script

Uso:
  python organizar_mods.py                          -> sincroniza todo
  python organizar_mods.py --excluir mobs sounds    -> sincroniza sin esas carpetas
  python organizar_mods.py --solo terrain libs      -> solo esas carpetas (+ .jar sueltos)
  python organizar_mods.py --limpiar                -> quita de `mods` lo que puso el script
  python organizar_mods.py --base "D:\\mi\\instancia" --dry-run

Usa enlaces duros (no duplica espacio en disco en la misma unidad); si no puede, copia.
Solo toca los archivos que el propio script creo (los anota en .sincronizado.json),
asi que cualquier otro .jar que pongas a mano en `mods` no se borra.
"""
import argparse, json, os, shutil, sys
from pathlib import Path

MANIFIESTO = ".sincronizado.json"

def default_minecraft_dir():
    if sys.platform.startswith("win"):
        return Path(os.environ.get("APPDATA", Path.home())) / ".minecraft"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/minecraft"
    return Path.home() / ".minecraft"

def limpiar(mods, dry):
    man = mods / MANIFIESTO
    if not man.exists():
        return 0
    anteriores = json.load(open(man, encoding="utf-8"))
    n = 0
    for nombre in anteriores:
        f = mods / nombre
        if f.exists():
            n += 1
            if not dry:
                f.unlink()
    if not dry:
        man.unlink()
    return n

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=str(default_minecraft_dir()))
    ap.add_argument("--biblioteca", default="mods_biblioteca", help="nombre de la carpeta biblioteca")
    ap.add_argument("--mods", default="mods", help="nombre de la carpeta que lee Minecraft")
    ap.add_argument("--excluir", nargs="*", default=[], help="subcarpetas a omitir")
    ap.add_argument("--solo", nargs="*", default=[], help="usar solo estas subcarpetas")
    ap.add_argument("--limpiar", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    base = Path(a.base)
    biblioteca, mods = base / a.biblioteca, base / a.mods
    if not biblioteca.is_dir():
        sys.exit(f"No existe la biblioteca: {biblioteca}\n"
                 f"Renombra tu carpeta de mods a '{a.biblioteca}' (o usa --base/--biblioteca).")
    mods.mkdir(exist_ok=True)

    quitados = limpiar(mods, a.dry_run)
    print(f"Quitados de '{a.mods}': {quitados}")
    if a.limpiar:
        return

    excluir = {e.lower() for e in a.excluir}
    solo = {s.lower() for s in a.solo}
    puestos, vistos, enlazados = [], {}, 0
    for jar in sorted(biblioteca.rglob("*.jar")):
        rel = jar.relative_to(biblioteca)
        carpeta = rel.parts[0].lower() if len(rel.parts) > 1 else None
        if carpeta and carpeta in excluir:
            continue
        if solo and carpeta and carpeta not in solo:
            continue
        if jar.name in vistos:
            print(f"AVISO: duplicado omitido: {rel} (ya esta {vistos[jar.name]})")
            continue
        vistos[jar.name] = rel
        destino = mods / jar.name
        if destino.exists():
            print(f"AVISO: '{jar.name}' ya existe en '{a.mods}' y no es del script; se deja igual.")
            continue
        if not a.dry_run:
            try:
                os.link(jar, destino)
                enlazados += 1
            except OSError:
                shutil.copy2(jar, destino)
        puestos.append(jar.name)

    if not a.dry_run:
        json.dump(puestos, open(mods / MANIFIESTO, "w", encoding="utf-8"), indent=1)
    print(f"{'(simulacion) ' if a.dry_run else ''}Puestos en '{a.mods}': {len(puestos)} "
          f"({enlazados} enlaces duros, {len(puestos) - enlazados} copias)")

if __name__ == "__main__":
    main()
