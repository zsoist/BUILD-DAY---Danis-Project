"""simcolombia/pipeline/build_pool_geih.py

Construye el POOL de personas reales GEIH desde los ZIP mensuales de data/raw_v2/.
Une 'Características generales' con 'Ocupados' por (DIRECTORIO, SECUENCIA_P, ORDEN)
dentro de cada mes y escribe data/pool_geih.json.gz (gzip, lista de dicts compactos).
Lectura streaming por archivo (zipfile directo, csv+latin-1; sin pandas).

Uso:  uv --project orchestrator run python simcolombia/pipeline/build_pool_geih.py
"""

from __future__ import annotations

import csv
csv.field_size_limit(10_000_000)
import gzip
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

# ------------------------------------------------------------------------- rutas
BASE = Path(__file__).resolve().parents[1]          # simcolombia/
RAW = BASE / "data" / "raw_v2"
OUT = BASE / "data" / "pool_geih.json.gz"

_BOM = "\ufeff\u00ef\u00bb\u00bf"                    # BOM utf-8 leído como latin-1


# ------------------------------------------------------------------------- utils

def _clean(v):
    """Campo crudo del CSV -> str sin espacios."""
    return (v or "").strip()


def _int_or_none(v):
    """Campo crudo -> int o None (vacío/no numérico -> None)."""
    v = _clean(v)
    if not v:
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


def _float0(v):
    """Campo crudo -> float (0.0 si no es numérico)."""
    try:
        return float(_clean(v))
    except ValueError:
        return 0.0


def _edu_map():
    """P3042 -> {ninguna, primaria, secundaria, media, superior}."""
    m = {}
    for n in range(1, 14):
        if n <= 2:
            m[str(n)] = "ninguna"        # ninguno / preescolar
        elif n == 3:
            m[str(n)] = "primaria"
        elif n == 4:
            m[str(n)] = "secundaria"
        elif n == 5:
            m[str(n)] = "media"
        else:
            m[str(n)] = "superior"       # 6..13
    return m


EDU = _edu_map()


def _find(names, needle):
    """Módulo CSV del ZIP cuyo NOMBRE BASE contiene `needle`.
    Solo .csv (los zips traen DTA/ y SAV/ binarios que envenenan el parser)
    y jamás los que empiezan por 'no ' ('No ocupados' != 'Ocupados')."""
    low = needle.lower()
    for n in names:
        base = n.rsplit("/", 1)[-1].lower()
        if not base.endswith(".csv"):
            continue
        if base.startswith("no "):
            continue
        if low in base:
            return n
    return None


def _rows(text):
    """Genera dicts fila a fila con cabecera normalizada (delimitador ';')."""
    reader = csv.reader(text, delimiter=";")
    try:
        header = next(reader)
    except StopIteration:
        return
    header = [h.strip().lstrip(_BOM) for h in header]
    for raw in reader:
        yield dict(zip(header, raw))


def _key(row):
    """Llave de persona (DIRECTORIO, SECUENCIA_P, ORDEN)."""
    return (row.get("DIRECTORIO", "").strip(),
            row.get("SECUENCIA_P", "").strip(),
            row.get("ORDEN", "").strip())


def _oficio(v):
    """OFICIO_C8 (CIUO-08) -> str de 4 dígitos o None."""
    v = _clean(v)
    if not v:
        return None
    n = _int_or_none(v)
    return str(n).zfill(4) if n is not None else v


def _rama(v):
    """RAMA2D_R4 (CIIU rev4) -> str de 2 dígitos o None."""
    v = _clean(v)
    if not v:
        return None
    n = _int_or_none(v)
    return f"{n:02d}" if n is not None else v


# -------------------------------------------------------------------- lectura mes

def _read_month(path):
    """Lee un ZIP mensual -> lista de dicts de persona (fex sin escalar)."""
    people = []
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        car = _find(names, "caracter")           # Características generales
        if car is None:
            raise FileNotFoundError(f"{path.name}: falta módulo Características")
        ocu = _find(names, "ocupados")           # Ocupados

        # índice de ocupados (mismo mes) -> (oficio, rama, ingreso, horas)
        index = {}
        if ocu is not None:
            with zf.open(ocu) as fh:
                text = io.TextIOWrapper(fh, encoding="latin-1", newline="")
                for row in _rows(text):
                    index[_key(row)] = (
                        _oficio(row.get("OFICIO_C8")),
                        _rama(row.get("RAMA2D_R4")),
                        _int_or_none(row.get("INGLABO")),
                        _int_or_none(row.get("P6800")),
                    )

        # todas las personas (Características)
        with zf.open(car) as fh:
            text = io.TextIOWrapper(fh, encoding="latin-1", newline="")
            for row in _rows(text):
                edad = _int_or_none(row.get("P6040"))
                if edad is None or edad < 0:
                    continue
                fex = _float0(row.get("FEX_C18"))
                if fex <= 0:
                    continue
                edu = _clean(row.get("P3042"))
                info = index.get(_key(row))
                people.append({
                    "dpto": _clean(row.get("DPTO")) or None,
                    "edad": edad,
                    "sexo": "hombre" if _clean(row.get("P3271")) == "1" else "mujer",
                    "educacion": EDU.get(edu) if edu else None,
                    "clase": "urbano" if _clean(row.get("CLASE")) == "1" else "rural",
                    # AREA: la GEIH marca a las 23 ciudades principales (código = su dpto).
                    # Vacío = otro municipio. Es dato real: dice quién vive en la capital.
                    "area": _clean(row.get("AREA")) or None,
                    "fex": fex,
                    "oficio_ciuo": info[0] if info else None,
                    "rama2d": info[1] if info else None,
                    "ingreso": info[2] if info else None,
                    "horas": info[3] if info else None,
                })
    return people


# ------------------------------------------------------------------------- main

def main():
    """Construye el pool, escribe el .json.gz y reporta el resumen."""
    zips = sorted(RAW.glob("geih_2025_*.zip")) + sorted(RAW.glob("geih_2026_*.zip"))
    if not zips:
        raise SystemExit(f"No hay ZIPs geih_2025_*/geih_2026_* en {RAW}")

    pool = []
    meses = 0
    for zp in zips:
        personas = _read_month(zp)
        if not personas:
            print(f"  [!] {zp.name}: sin filas válidas, omitido")
            continue
        pool.extend(personas)
        meses += 1
        print(f"  [+] {zp.name}: {len(personas):>8,} personas")

    if not pool:
        raise SystemExit("Pool GEIH vacío")

    # fex mensual / nº de meses usados -> el pool agrega como población promedio
    if meses > 1:
        for p in pool:
            p["fex"] /= meses

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(pool, fh, ensure_ascii=False, separators=(",", ":"))

    # ------------------------------------------------------------- resumen
    total = len(pool)
    dptos = Counter(p["dpto"] for p in pool)
    con_oficio = sum(1 for p in pool if p["oficio_ciuo"] is not None)

    print("\n=== POOL GEIH ===")
    print(f"Personas totales : {total:,}")
    print(f"Meses usados     : {meses}  (fex /= {meses})")
    print(f"Con oficio       : {con_oficio:,}  ({100 * con_oficio / total:.1f}%)")
    print("Top-5 dpto:")
    for d, c in dptos.most_common(5):
        print(f"  {str(d):>4}  {c:>8,}  ({100 * c / total:5.1f}%)")
    print(f"Salida           : {OUT}")


if __name__ == "__main__":
    main()
