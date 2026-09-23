#!/usr/bin/env python3
"""ECV 2025, microdatos (bienestar subjetivo de 15+) → celdas agregadas por departamento.

Módulo "Características y composición del hogar" (P1895-P1905, P3175, P1927: escalas 0-10)
unido por DIRECTORIO+SECUENCIA_P+ORDEN a "Variables diseño muestral" (MPIO: los 2 primeros
dígitos son el departamento; el municipio capital es <dpto>001). Salida, solo agregados
(ninguna celda con menos de MIN_N encuestados reales; si no alcanza, se omite y manda el
margen de más arriba):
  web/opinion/ECV_<ítem>.json   {"*": nacional, "dcap": {"70|capital": …, "70|resto": …},
                                 "sexo": {1,2}, "ge3": {0,1,2}}

  uv run --with pyreadstat --with pandas --python 3.12 python simcolombia/pipeline/ecv_micro.py
Los .zip los baja una persona (el catálogo del DANE tiene reCAPTCHA) a ~/Downloads o a
simcolombia/data/raw_v2/ecv2025/.
"""
import json
import shutil
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pyreadstat

RAIZ = Path(__file__).resolve().parents[2]
DIR = RAIZ / "simcolombia" / "data" / "raw_v2" / "ecv2025"
OUT = RAIZ / "web" / "opinion"
MIN_N = 30
LLAVE = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
# ítem → (código, texto como lo preguntaría una persona, afirmativas en la escala 0-10)
ITEMS = {
    "vida": ("P1895", "¿Qué tan satisfecho se siente con su vida actualmente?", "7-10"),
    "ingreso": ("P1896", "¿Qué tan satisfecho se siente con su ingreso actualmente?", "7-10"),
    "salud": ("P1897", "¿Qué tan satisfecho se siente con su salud actualmente?", "7-10"),
    "seguridad": ("P1898", "¿Qué tan satisfecho se siente con su nivel de seguridad actualmente?", "7-10"),
    "trabajo": ("P1899", "¿Qué tan satisfecho se siente con su trabajo o actividad actualmente?", "7-10"),
    "tiempo_libre": ("P3175", "¿Qué tan satisfecho se siente con su tiempo libre?", "7-10"),
    "feliz": ("P1901", "¿Qué tan feliz se sintió ayer?", "7-10"),
    "preocupado": ("P1903", "¿Qué tan preocupado se sintió ayer?", "6-10"),
    "triste": ("P1904", "¿Qué tan triste se sintió ayer?", "6-10"),
    "vale_pena": ("P1905", "¿Qué tanto considera que las cosas que hace en su vida valen la pena?", "7-10"),
    "escalon": ("P1927", "En una escalera de 0 a 10, donde 10 es la mejor vida posible, ¿en cuál escalón se encuentra hoy?", "7-10"),
}
# solo los extremos llevan nombre (como LAPOP): sin ellos, «6» a secas no le dice nada a la voz
EXTREMOS = {"feliz": ("nada", "completamente"), "preocupado": ("nada", "completamente"), "triste": ("nada", "completamente"),
            "vale_pena": ("nada", "completamente"), "escalon": ("la peor vida posible", "la mejor vida posible")}


def sav(nombre_zip, destino):
    """Saca el .sav del zip del DANE (los nombres internos vienen en otra codificación)."""
    dst = DIR / destino
    if dst.exists():
        return dst
    for base in (DIR, Path.home() / "Downloads"):
        z = base / nombre_zip
        if z.exists():
            with zipfile.ZipFile(z) as zf:
                i = next(i for i in zf.infolist() if i.filename.lower().endswith(".sav"))
                with zf.open(i) as s, open(dst, "wb") as d:
                    shutil.copyfileobj(s, d)
            return dst
    sys.exit(f"falta {nombre_zip} (en ~/Downloads o {DIR})")


def dist(df, col):
    v = df[col]
    ok = v.between(0, 10)
    w = df.loc[ok, "FEX_C"]
    if ok.sum() < MIN_N:
        return None
    t = w.groupby(v[ok].astype(int)).sum()
    return {str(k): round(float(x / w.sum()), 4) for k, x in t.items()}


def main():
    DIR.mkdir(parents=True, exist_ok=True)
    car, _ = pyreadstat.read_sav(sav("DBF-ECV-Caracteristicas_composicion_hogar-2025.zip", "caracteristicas_2025.sav"),
                                 usecols=LLAVE + ["FEX_C", "P6020", "P6040"] + [c for c, _, _ in ITEMS.values()])
    dis, _ = pyreadstat.read_sav(sav("DBF-ECV-Variables_diseno_muestral-2025.zip", "diseno_2025.sav"), usecols=LLAVE + ["MPIO"])
    for d in (car, dis):
        for k in LLAVE:
            d[k] = d[k].astype(str).str.strip()
    df = car.merge(dis.drop_duplicates(LLAVE), on=LLAVE, how="left")
    print(f"{len(df)} personas · con municipio: {df['MPIO'].notna().mean():.1%}")
    mp = df["MPIO"].astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(5)
    df["dpto"] = mp.str[:2]
    df["dcap"] = df["dpto"] + "|" + (mp.str[2:] == "001").map({True: "capital", False: "resto"})
    df["sexo"] = df["P6020"].map({1: "1", 2: "2"})
    df["ge3"] = pd.cut(df["P6040"], [-1, 24, 54, 200], labels=["0", "1", "2"]).astype(str)
    banco = []
    for clave, (col, texto, af) in ITEMS.items():
        base = df[df[col].between(0, 10)]
        D = {"*": dist(base, col)}
        for dim in ("dcap", "sexo", "ge3"):
            D[dim] = {k: x for k, g in base.groupby(dim) if (x := dist(g, col))}
        (OUT / f"ECV_{clave}.json").write_text(json.dumps(D, ensure_ascii=False, separators=(",", ":")))
        a, b = map(int, af.split("-"))
        banco.append({"codigo": f"ECV:{clave}", "fuente": "DANE ECV 2025 (microdatos, por departamento)", "texto": texto,
                      "escala": [0, 10],
                      "opciones": dict(zip(("0", "10"), EXTREMOS.get(clave, ("totalmente insatisfecho", "totalmente satisfecho")))), "afirmativas": [str(k) for k in range(a, b + 1)],
                      "sustantivas": [str(k) for k in range(11)]})
        s = D["dcap"].get("70|capital"), D["dcap"].get("70|resto")
        pos = lambda d: round(100 * sum(v for k, v in d.items() if a <= int(k) <= b), 1) if d else None
        print(f"  {clave:13} nacional {pos(D['*'])}% · Sincelejo {pos(s[0])}% · resto de Sucre {pos(s[1])}% · celdas dpto {len(D['dcap'])}")
    (RAIZ / "simcolombia" / "data" / "ecv_micro_banco.json").write_text(json.dumps(banco, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
