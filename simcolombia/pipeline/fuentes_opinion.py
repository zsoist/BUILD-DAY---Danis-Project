#!/usr/bin/env python3
"""Donantes de LAPOP 2023 y Latinobarómetro 2024 para las personas sintéticas.

Mismo esquema que donantes_ecp.py (ECP del DANE), para temas que la ECP no
pregunta: economía, corrupción, migración, paz, cambio climático.

LICENCIA — importa más que el código: LAPOP prohíbe "distribuir, compartir o
publicar los datos en cualquier forma" y permite solo reportar agregados.
Por eso TODO lo que sale de aquí por persona se escribe en data/raw_v2/, que
está en .gitignore y no se despliega. Nada de estas fuentes va a web/.

Los microdatos se bajan a mano (ver docs/METODO.md):
  raw_v2/COL_2023_LAPOP_AmericasBarometer_v1.0_w.sav
  raw_v2/latinobarometro-2024-spss.zip

  uv run python simcolombia/pipeline/fuentes_opinion.py
"""
import hashlib
import json
import sys
import unicodedata
import zipfile
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyreadstat

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "simcolombia" / "data" / "raw_v2"
sys.path.insert(0, str(Path(__file__).parent))
from donantes_ecp import REGION, grupo_edad, grupo_edu_res  # noqa: E402  mismo emparejamiento


def _norm(s):
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()
    return " ".join(s.replace(",", " ").replace(".", " ").split())


def _dptos():
    """nombre normalizado de departamento → código DANE, desde los residentes"""
    res = json.loads((RAIZ / "web" / "residents_v2.json").read_text())
    res = res if isinstance(res, list) else res["residentes"]
    d = {_norm(r["dpto_nombre"]): r["dpto"] for r in res}
    d.update({"bogota d c": "11", "bogota": "11", "narino": "52", "choco": "27",
              "san andres": "88", "valle": "76", "norte santander": "54"})
    return d


def lapop():
    df, m = pyreadstat.read_sav(RAW / "COL_2023_LAPOP_AmericasBarometer_v1.0_w.sav")
    # 888888 (no sabe), 988888 (no responde), 999999 (no aplica) y similares
    num = df.apply(pd.to_numeric, errors="coerce").mask(lambda x: x >= 888000)
    edre = num["edre"]
    base = pd.DataFrame({
        "region": num["prov"].map(lambda p: REGION.get(f"{int(p) - 800:02d}") if p == p else None),
        "sexo": num["q1tc_r"],
        "edad": num["q2"],
        "edu": edre.map(lambda e: None if e != e else 0 if e <= 2 else 1 if e <= 4 else 2),
        "peso": num["wt"],
    })
    return base, num, m


def latinobarometro():
    with zipfile.ZipFile(RAW / "latinobarometro-2024-spss.zip") as z:
        sav = next(n for n in z.namelist() if n.endswith(".sav"))
        z.extract(sav, "/tmp/lb")
    df, m = pyreadstat.read_sav(f"/tmp/lb/{sav}")
    df = df[df["IDENPA"] == 170]
    num = df.apply(pd.to_numeric, errors="coerce")
    # la región sale del departamento de la ciudad: REG agrupa Tolima, Meta,
    # Huila y Caquetá en una sola, que en la ECP son dos regiones distintas
    dp, ciu = _dptos(), m.variable_value_labels.get("CIUDAD", {})

    def reg(c):
        nombre = _norm(str(ciu.get(c, "")).replace("CO:", "").split("-")[0])
        return REGION.get(dp.get(nombre))
    ed = num["REEDUC.1"]
    base = pd.DataFrame({
        "region": num["CIUDAD"].map(reg),
        "sexo": num["SEXO"],
        "edad": num["EDAD"],
        "edu": ed.map(lambda e: None if e != e else 0 if e <= 3 else 1 if e <= 5 else 2),
        "peso": num["WT"],
    }, index=num.index)
    return base, num, m


def donantes(base, num, items, semilla_fuente):
    """Para cada residente adulto, las respuestas de un donante de su celda."""
    ok = base.dropna(subset=["region", "sexo", "edad", "edu"])
    celdas = defaultdict(list)
    for i, f in ok.iterrows():
        clave = (int(f["region"]), int(f["sexo"]), grupo_edad(f["edad"]), int(f["edu"]))
        resp = [None if v != v else int(v) for v in num.loc[i, items]]
        celdas[clave].append((float(f["peso"] or 0), resp))

    def elegir(cands, semilla):
        tot = sum(c[0] for c in cands)
        x = (int(hashlib.sha256(semilla.encode()).hexdigest(), 16) % 10**9) / 10**9 * tot
        for c in cands:
            x -= c[0]
            if x <= 0:
                return c[1]
        return cands[-1][1]

    res = json.loads((RAIZ / "web" / "residents_v2.json").read_text())
    res = res if isinstance(res, list) else res["residentes"]
    por_id, nivel = {}, defaultdict(int)
    for r in res:
        if r["edad"] < 18:
            continue
        reg, sx = REGION.get(r["dpto"]), 1 if r["sexo"] == "hombre" else 2
        ge, gu = grupo_edad(r["edad"]), grupo_edu_res(r["educacion"])
        for n, clave in enumerate([(reg, sx, ge, gu), (reg, sx, ge, None),
                                   (reg, None, ge, None), (reg, None, None, None),
                                   (None, sx, ge, gu)]):
            cands = [c for k, v in celdas.items()
                     if all(a is None or a == b for a, b in zip(clave, k)) for c in v]
            if len(cands) >= 5:
                por_id[r["id"]] = elegir(cands, semilla_fuente + r["id"])
                nivel[n] += 1
                break
    return por_id, nivel, len(ok)


def main():
    for nombre, cargar, archivo in (("LAPOP 2023", lapop, "lapop"),
                                    ("Latinobarómetro 2024", latinobarometro, "lb")):
        base, num, m = cargar()
        items = [c for c in num.columns if c in m.variable_value_labels and num[c].notna().sum() >= 300]
        por_id, nivel, n_ok = donantes(base, num, items, archivo)
        (RAW / f"respuestas_{archivo}.json").write_text(json.dumps(
            {"fuente": nombre, "items": items, "por_id": por_id}, separators=(",", ":")))
        n = sum(nivel.values())
        print(f"{nombre}: {n_ok} encuestados con demografía completa · {len(items)} variables · {n} residentes con donante")
        for k, et in enumerate(["región·sexo·edad·educación", "sin educación", "solo región·edad", "solo región", "sin región"]):
            if nivel[k]:
                print(f"    {et:<28} {nivel[k]:>5} ({100 * nivel[k] / n:.1f}%)")


if __name__ == "__main__":
    main()
