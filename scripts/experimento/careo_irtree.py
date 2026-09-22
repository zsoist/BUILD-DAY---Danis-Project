#!/usr/bin/env python3
"""Careo con discretización psicométrica: calibra el IRTree en UNA pregunta y lo
valida en OTRA que nunca vio.

Calibrar y validar en la misma pregunta sería enseñarle al examen. Aquí los
parámetros poblacionales de estilo de respuesta se ajustan una sola vez contra
las marginales de la pregunta de calibración, y después se aplican tal cual a la
pregunta de validación.

Uso:
  uv run --with pyreadstat --with pandas --python 3.12 python \
    scripts/experimento/careo_irtree.py <calibracion.json> <validacion.json>
"""
import json
import os
import sys
import tempfile
import zipfile
from pathlib import Path

import pyreadstat

sys.path.insert(0, str(Path(__file__).resolve().parent))
from irtree import BASE, calibrar, marginales, w1  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "simcolombia" / "data" / "raw_v2"
CAL_OUT = Path(__file__).resolve().parent / "irtree_calibracion.json"
NS = 99
TMP = tempfile.mkdtemp()


def cargar(zip_nombre):
    with zipfile.ZipFile(RAW / zip_nombre) as z:
        sav = next(n for n in z.namelist() if n.endswith(".sav"))
        z.extract(sav, TMP)
    return pyreadstat.read_sav(os.path.join(TMP, sav))[0]


def humano(codigo, demo, viv_col, viv):
    """Marginales humanas ponderadas + tasa de 'no sé'."""
    d = demo
    if viv_col:
        d = d.merge(viv[["DIRECTORIO", viv_col]].drop_duplicates("DIRECTORIO"),
                    on="DIRECTORIO", how="left")
        pesos = d[viv_col].fillna(0).tolist()
    else:
        pesos = None
    vals = d[codigo].tolist()
    c = {k: 0.0 for k in range(1, 6)}
    tot = 0.0
    for i, v in enumerate(vals):
        if v is None or v != v or int(v) not in c:
            continue
        w = 1.0 if pesos is None else float(pesos[i])
        c[int(v)] += w
        tot += w
    validos = [v for v in vals if v == v]
    ns = sum(1 for v in validos if v == NS) / max(1, len(validos))
    return {k: (v / tot if tot else 0.0) for k, v in c.items()}, ns


def sd_de(p):
    mu = sum(k * v for k, v in p.items())
    return (sum(v * (k - mu) ** 2 for k, v in p.items())) ** 0.5, mu


def tabla(nombre, p_sin, ns_sin, p_hum, ns_hum):
    sd_s, mu_s = sd_de(p_sin)
    sd_h, mu_h = sd_de(p_hum)
    d = w1(p_sin, p_hum)
    print(f"\n{nombre}")
    print(f"{'opción':<12}{'humanos':>10}{'sintéticos':>13}{'dif':>11}")
    print("-" * 46)
    for k in range(1, 6):
        print(f"{k:<12}{100*p_hum[k]:>9.1f}%{100*p_sin[k]:>12.1f}%{100*(p_sin[k]-p_hum[k]):>+10.1f}")
    print("-" * 46)
    print(f"{'media':<12}{mu_h:>10.2f}{mu_s:>13.2f}")
    print(f"{'desv. est.':<12}{sd_h:>10.2f}{sd_s:>13.2f}   razón {sd_s/sd_h:.2f}")
    print(f"{'no sé':<12}{100*ns_hum:>9.1f}%{100*ns_sin:>12.1f}%")
    print(f"W1 = {d:.3f}")
    return d, sd_s / sd_h if sd_h else 0


def main():
    cal = json.loads(Path(sys.argv[1]).read_text())
    val = json.loads(Path(sys.argv[2]).read_text())
    for x in (cal, val):
        if x.get("modo") != "continuo":
            sys.exit("los dos archivos deben venir del modo continuo")

    demo = cargar("ecp2023_democracia.zip")
    try:
        viv = cargar("ecp2023_viviendas.zip")
        viv_col = next((c for c in viv.columns if c.upper().startswith("FEX")), None)
    except Exception:
        viv, viv_col = None, None

    pares_cal = [(r["id"], r["resp"]) for r in cal["respuestas"] if r["resp"] is not None]
    pares_val = [(r["id"], r["resp"]) for r in val["respuestas"] if r["resp"] is not None]
    h_cal, ns_cal = humano(cal["codigo"], demo, viv_col, viv)
    h_val, ns_val = humano(val["codigo"], demo, viv_col, viv)

    print(f"CALIBRACIÓN en {cal['codigo']} (n={len(pares_cal)}) · "
          f"VALIDACIÓN en {val['codigo']} (n={len(pares_val)})")

    m0, n0 = marginales(pares_cal, BASE)
    d0, _ = tabla(f"[{cal['codigo']}] SIN calibrar (parámetros de arranque)",
                  m0, n0, h_cal, ns_cal)

    par, coste = calibrar(pares_cal, h_cal, ns_cal)
    print(f"\nparámetros calibrados: e_mu={par['e_mu']:.2f} e_sd={par['e_sd']:.2f} "
          f"s_mu={par['s_mu']:.2f} g_mu={par['g_mu']:.2f}  (coste {coste:.4f})")
    CAL_OUT.write_text(json.dumps(
        {"calibrado_en": cal["codigo"], "n": len(pares_cal), "parametros": par},
        ensure_ascii=False, indent=1))

    m1, n1 = marginales(pares_cal, par)
    tabla(f"[{cal['codigo']}] CALIBRADO (la pregunta que sí vio)", m1, n1, h_cal, ns_cal)

    m2, n2 = marginales(pares_val, par)
    d2, r2 = tabla(f"[{val['codigo']}] VALIDACIÓN — pregunta NUNCA vista", m2, n2, h_val, ns_val)

    unif = {k: 0.2 for k in range(1, 6)}
    modo_k = max(h_val, key=h_val.get)
    modo = {k: (1.0 if k == modo_k else 0.0) for k in range(1, 6)}
    print(f"\nEn la pregunta de validación:")
    print(f"  baseline azar            = {w1(unif, h_val):.3f}")
    print(f"  baseline lo más común    = {w1(modo, h_val):.3f}")
    print(f"  IRTree calibrado         = {d2:.3f}   "
          f"{'LE GANA' if d2 < min(w1(unif,h_val), w1(modo,h_val)) else 'NO le gana'}")
    print(f"  razón de desviación      = {r2:.2f}   (objetivo 1.00)")


if __name__ == "__main__":
    main()
