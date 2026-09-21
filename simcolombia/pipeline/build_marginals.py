#!/usr/bin/env python3
"""Normaliza data/raw/ → data/marginals.json (el contrato del generador).

Esquema por departamento (código DIVIPOLA de 2 dígitos):
  nombre, poblacion, sexo{hombre,mujer}, edad{grupo→n} (por sexo si existe),
  urbano_pct, pib_sectores{actividad→pct}, salud{contributivo,subsidiado,otro}
Cada bloque lleva su fuente. Falta un bloque → se omite, JAMÁS se inventa.
"""
import csv
import io
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW, OUT = BASE / "data" / "raw", BASE / "data" / "marginals.json"

DPTOS = {  # DIVIPOLA — 32 departamentos + Bogotá D.C.
 "05":"Antioquia","08":"Atlántico","11":"Bogotá D.C.","13":"Bolívar","15":"Boyacá",
 "17":"Caldas","18":"Caquetá","19":"Cauca","20":"Cesar","23":"Córdoba",
 "25":"Cundinamarca","27":"Chocó","41":"Huila","44":"La Guajira","47":"Magdalena",
 "50":"Meta","52":"Nariño","54":"Norte de Santander","63":"Quindío","66":"Risaralda",
 "68":"Santander","70":"Sucre","73":"Tolima","76":"Valle del Cauca","81":"Arauca",
 "85":"Casanare","86":"Putumayo","88":"San Andrés y Providencia","91":"Amazonas",
 "94":"Guainía","95":"Guaviare","97":"Vaupés","99":"Vichada",
}
def norm(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z ]","",s).strip()
NAME2COD = {norm(v): k for k, v in DPTOS.items()}
NAME2COD.update({"bogota dc":"11","bogota":"11","san andres":"88",
                 "archipielago de san andres providencia y santa catalina":"88",
                 "archipielago de san andres":"88","norte santander":"54",
                 "valle":"76","la guajira":"44"})

def dep(code_or_name):
    c = str(code_or_name or "").strip()
    if c[:2].isdigit():
        return c.zfill(2)[:2] if c.zfill(2)[:2] in DPTOS else None
    return NAME2COD.get(norm(c))

M = {k: {"nombre": v, "fuentes": {}} for k, v in DPTOS.items()}

# ── PIB por actividad (kgyi-qc7j): estructura económica → ocupaciones ──
pib = json.loads((RAW / "pib_departamental.json").read_text())
years = [r.get("a_o") for r in pib if r.get("a_o")]
last = max(years)
acc = defaultdict(lambda: defaultdict(float))
for r in pib:
    if r.get("a_o") != last or "corrientes" not in (r.get("tipo_de_precios") or ""):
        continue
    d = dep(r.get("c_digo_departamento_divipola") or r.get("departamento"))
    if d:
        try: acc[d][r.get("actividad","?")] += float(r.get("valor_miles_de_millones_de") or 0)
        except ValueError: pass
for d, sect in acc.items():
    tot = sum(sect.values()) or 1
    top = dict(sorted(((k, round(v/tot*100,1)) for k,v in sect.items()),
                      key=lambda x:-x[1])[:6])
    M[d]["pib_sectores_pct"] = top
    M[d]["fuentes"]["pib"] = f"DANE PIB dptal {last} (datos.gov.co kgyi-qc7j)"

# ── Salud (23gb-dhmd, municipal → dpto por DIVIPOLA) ──
sal = json.loads((RAW / "salud_municipios.json").read_text())
years_s = sorted({r.get("periodo") for r in sal if r.get("periodo")})
last_s = years_s[-1]
agg = defaultdict(lambda: defaultdict(float))
for r in sal:
    if r.get("periodo") != last_s: continue
    d = (r.get("codigo") or "")[:2]
    if d not in DPTOS: continue
    for k, col in [("contributivo","cobertura_regimen_contributivo"),
                   ("subsidiado","cobertura_regimen_subsidiado"),
                   ("total","cobertura_total")]:
        try: agg[d][k] += float(r.get(col) or 0)
        except ValueError: pass
for d, v in agg.items():
    if v.get("total"):
        M[d]["salud_pct"] = {"contributivo": round(v["contributivo"]/v["total"]*100,1),
                             "subsidiado": round(v["subsidiado"]/v["total"]*100,1)}
        M[d]["fuentes"]["salud"] = f"MinSalud cobertura {last_s} (datos.gov.co 23gb-dhmd)"

# ── Educación (CNPV 2018 cuadro 17PD, pre-extraído a JSON) ──
edu_f = RAW / "educacion_dpto.json"
if edu_f.exists():
    for d, pct in json.loads(edu_f.read_text()).items():
        if d in M:
            M[d]["educacion_pct"] = pct
            M[d]["fuentes"]["educacion"] = "CNPV 2018 cuadro 17PD (nivel alcanzado, 5+ años)"

# ── Proyecciones DANE dpto×sexo×edad simple (xlsx oficial, hoja PPODeptos) ──
AÑO_SIM = 2026
proy = RAW / "proyecciones_dane.xlsx"
if proy.exists():
    from openpyxl import load_workbook
    wb = load_workbook(proy, read_only=True, data_only=True)
    ws = wb["PPODeptos"] if "PPODeptos" in wb.sheetnames else wb[wb.sheetnames[0]]
    rows = ws.iter_rows(values_only=True)
    header = None
    for row in rows:
        if row and any(c == "DP" for c in row if c):
            header = list(row)
            break
    idx = {c: i for i, c in enumerate(header)}
    h_cols = [(a, idx[f"Hombres_{a}"]) for a in range(101) if f"Hombres_{a}" in idx]
    m_cols = [(a, idx[f"Mujeres_{a}"]) for a in range(101) if f"Mujeres_{a}" in idx]
    grupos = [(a, f"{a}-{a+4}") for a in range(0, 85, 5)]

    def grupo(a):
        return "85+" if a >= 85 else next(g for lo, g in reversed(grupos) if a >= lo)

    tot_area = {}
    n_ok = 0
    for row in rows:
        if not row or row[idx["AÑO"]] != AÑO_SIM:
            continue
        d = str(row[idx["DP"]]).zfill(2)
        if d not in DPTOS:
            continue
        area = str(row[idx["ÁREA GEOGRÁFICA"]])
        total = sum(row[i] or 0 for _, i in h_cols) + sum(row[i] or 0 for _, i in m_cols)
        if area == "Cabecera":
            tot_area.setdefault(d, {})["cab"] = total
        elif area == "Total":
            tot_area.setdefault(d, {})["tot"] = total
            edad, edad_sexo = defaultdict(int), {"hombre": defaultdict(int), "mujer": defaultdict(int)}
            for a, i in h_cols:
                edad[grupo(a)] += row[i] or 0
                edad_sexo["hombre"][grupo(a)] += row[i] or 0
            for a, i in m_cols:
                edad[grupo(a)] += row[i] or 0
                edad_sexo["mujer"][grupo(a)] += row[i] or 0
            M[d]["poblacion"] = int(total)
            M[d]["sexo"] = {"hombre": int(sum(row[i] or 0 for _, i in h_cols)),
                            "mujer": int(sum(row[i] or 0 for _, i in m_cols))}
            M[d]["edad"] = {g: int(n) for g, n in edad.items()}
            M[d]["edad_sexo"] = {s: {g: int(n) for g, n in gs.items()}
                                 for s, gs in edad_sexo.items()}
            M[d]["fuentes"]["poblacion"] = (
                f"DANE proyecciones CNPV2018 post-COVID, año {AÑO_SIM}, edades simples")
            n_ok += 1
    for d, v in tot_area.items():
        if v.get("tot"):
            M[d]["urbano_pct"] = round(v.get("cab", 0) / v["tot"] * 100, 1)
    print(f"proyecciones DANE {AÑO_SIM}: {n_ok}/33 dptos con sexo×edad, "
          f"{len(tot_area)}/33 con urbano_pct")
else:
    print("⚠️  sin proyecciones_dane.xlsx — sexo/edad pendientes")

json.dump({"generado":"2026-09-21","departamentos":M}, OUT.open("w"),
          ensure_ascii=False, indent=1)
listo = sum(1 for d in M.values() if len(d) > 2)
print(f"marginals.json: {listo}/33 dptos con datos → {OUT}")
