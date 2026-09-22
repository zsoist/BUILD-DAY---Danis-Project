#!/usr/bin/env python3
"""Baseline humano REAL: ¿cuánto predice la identidad demográfica la opinión
de un colombiano de carne y hueso?

Usa los microdatos de la Encuesta de Cultura Política (ECP) del DANE — la misma
casa que produce la GEIH de la que salen nuestros residentes. Calcula la V de
Cramér entre (edad, educación, sexo) y cada pregunta actitudinal del módulo de
democracia.

Ese número es el patrón contra el que se juzga el simulador: la literatura
documenta que los modelos de lenguaje SOBREDETERMINAN la identidad (tratan la
demografía como mucho más predictiva de lo que es). Sin este baseline, no hay
forma de saber si nuestras voces caricaturizan.

Requiere pyreadstat (los .sav del DANE vienen sin etiquetas, solo códigos):
  uv run --with pyreadstat --with pandas --python 3.12 python scripts/experimento/baseline_ecp.py
"""
import math
import os
import statistics as st
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    import pyreadstat
except ImportError:
    sys.exit("falta pyreadstat — corre con: uv run --with pyreadstat --with pandas "
             "--python 3.12 python scripts/experimento/baseline_ecp.py")

RAW = Path(__file__).resolve().parents[2] / "simcolombia" / "data" / "raw_v2"
ANIO = sys.argv[1] if len(sys.argv) > 1 else "2023"
LLAVES = ["DIRECTORIO", "NRO_ENCUESTA", "HOGAR_NUMERO", "PERSONA_NUMERO"]
EDAD, EDUCACION, SEXO = "P5785", "P6210", "P220"
TMP = tempfile.mkdtemp()


def cargar(zip_nombre):
    """Extrae el .sav del zip del DANE y lo lee."""
    ruta = RAW / zip_nombre
    if not ruta.exists():
        sys.exit(f"no encuentro {ruta} — ¿bajaste los microdatos de la ECP?")
    with zipfile.ZipFile(ruta) as z:
        sav = next(n for n in z.namelist() if n.endswith(".sav"))
        z.extract(sav, TMP)
    return pyreadstat.read_sav(os.path.join(TMP, sav))[0]


def banda_edad(a):
    return "18-29" if a < 30 else "30-44" if a < 45 else "45-59" if a < 60 else "60+"


def nivel_edu(x):
    """P6210 del DANE: 1-3 bajo · 4 medio · 5-7 alto · 9/99 sin dato."""
    if x is None or x != x or x >= 9:
        return None
    return "bajo" if x <= 3 else "medio" if x == 4 else "alto"


def cramers_v(df, dem, item):
    """V de Cramér entre dos columnas categóricas. None si la tabla es muy chica."""
    tabla = df.groupby([dem, item]).size().unstack(fill_value=0)
    n = int(tabla.values.sum())
    if n < 100 or min(tabla.shape) < 2:
        return None
    filas = tabla.sum(axis=1).values
    cols = tabla.sum(axis=0).values
    chi2 = 0.0
    for i, nf in enumerate(filas):
        for j, nc in enumerate(cols):
            esp = nf * nc / n
            if esp:
                chi2 += (tabla.values[i][j] - esp) ** 2 / esp
    k = min(tabla.shape) - 1
    return math.sqrt(chi2 / (n * k)) if k else None


def main():
    carac = cargar(f"ecp{ANIO}_caracteristicas.zip")
    demo = cargar(f"ecp{ANIO}_democracia.zip")
    m = demo.merge(carac[LLAVES + [EDAD, EDUCACION, SEXO]], on=LLAVES, how="inner")
    m = m[m[EDAD] >= 18]                      # universo ECP: adultos
    m["_edad"] = m[EDAD].apply(banda_edad)
    m["_edu"] = m[EDUCACION].apply(nivel_edu)

    # ítems actitudinales: columnas con 2-7 categorías y códigos pequeños
    items = []
    for c in demo.columns[len(LLAVES):]:
        if c not in m.columns:
            continue
        s = m[c].dropna()
        if s.empty:
            continue
        try:
            u = sorted(float(x) for x in s.unique())
        except (TypeError, ValueError):
            continue
        if 2 <= len(u) <= 7 and max(u) <= 10:
            items.append(c)

    res = {"_edad": [], "_edu": [SEXO][0:0], SEXO: []}
    res["_edu"] = []
    for c in items:
        sub = m[[c, "_edad", "_edu", SEXO]].dropna()
        for dem in ("_edad", "_edu", SEXO):
            v = cramers_v(sub, dem, c)
            if v is not None:
                res[dem].append(v)

    print(f"\nBASELINE HUMANO — ECP {ANIO} del DANE")
    print(f"n = {len(m):,} personas adultas · {len(items)} preguntas actitudinales\n")
    print(f"{'atributo de identidad':<26}{'mediana V':>11}{'media':>9}{'p90':>8}{'máx':>8}")
    print("-" * 62)
    for dem, nombre in (("_edad", "edad (4 bandas)"),
                        ("_edu", "educación (3 niveles)"),
                        (SEXO, "sexo")):
        v = sorted(res[dem])
        if not v:
            continue
        print(f"{nombre:<26}{st.median(v):>11.3f}{st.mean(v):>9.3f}"
              f"{v[int(0.9 * len(v))]:>8.3f}{max(v):>8.3f}")
    print("-" * 62)
    print("Lectura: en personas reales la identidad explica MUY POCO de la opinión.")
    print("Si el simulador produce V mucho mayores, está caricaturizando.")


if __name__ == "__main__":
    main()
