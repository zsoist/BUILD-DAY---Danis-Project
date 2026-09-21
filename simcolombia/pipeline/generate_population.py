#!/usr/bin/env python3
"""Genera los residentes sintéticos → dashboard/sim/residents.json
y el reporte de fidelidad → dashboard/sim/validacion.json.

Principio: cada atributo se muestrea del marginal REAL si existe; si un bloque
aún no tiene fuente, el atributo sale marcado "provisional" y el reporte lo
dice — nunca se disfraza un invento de dato.
Determinista (seed fija): la demo es reproducible.
"""
import json
import random
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DASH = BASE.parent / "dashboard" / "sim"
DASH.mkdir(parents=True, exist_ok=True)
N_POR_DPTO = 200
rng = random.Random(2026_09_21)

M = json.loads((BASE / "data" / "marginals.json").read_text())["departamentos"]
DOSSIERS = {}
ddir = BASE / "data" / "dossiers"
if ddir.exists():
    for f in ddir.glob("dossier_*.json"):
        try:
            d = json.loads(f.read_text())
            DOSSIERS[d["cod"]] = d
        except Exception:
            pass

# mapa sector PIB → oficios genéricos (se refina con el dossier del dpto)
SECTOR_OCUP = {
    "agricultura": ["agricultor(a)", "jornalero(a)", "ganadero(a)"],
    "comercio": ["comerciante", "tendero(a)", "vendedor(a)"],
    "manufactur": ["operario(a) de planta", "confeccionista"],
    "construc": ["maestro(a) de obra", "oficial de construcción"],
    "minas": ["minero(a)", "operador(a) petrolero(a)"],
    "administraci": ["funcionario(a) público(a)", "docente"],
    "financier": ["empleado(a) bancario(a)", "contador(a)"],
    "inmobiliar": ["administrador(a) de finca raíz"],
    "informaci": ["técnico(a) de sistemas"],
    "transporte": ["conductor(a)", "mototaxista"],
    "aloj": ["cocinero(a)", "mesero(a)", "hotelero(a)"],
}
EDADES = [("0-4",2),("5-9",7),("10-14",12),("15-19",17),("20-24",22),("25-29",27),
          ("30-34",32),("35-39",37),("40-44",42),("45-49",47),("50-54",52),
          ("55-59",57),("60-64",62),("65-69",67),("70-74",72),("75-79",77),
          ("80-84",82),("85+",88)]


def sample_w(pairs):
    total = sum(w for _, w in pairs)
    x = rng.uniform(0, total)
    for v, w in pairs:
        x -= w
        if x <= 0:
            return v
    return pairs[-1][0]


def ocupaciones(d, dpto):
    dos = DOSSIERS.get(dpto, {})
    base = list(dos.get("ocupaciones_tipicas", []))
    for sector, pct in d.get("pib_sectores_pct", {}).items():
        for k, ops in SECTOR_OCUP.items():
            if k in sector.lower():
                base += ops
    return base or ["trabajador(a) independiente"]


residents, provisional = [], set()
for cod, d in sorted(M.items()):
    dos = DOSSIERS.get(cod, {})
    edad_dist = d.get("edad")            # {"0-4": n, ...} si hay proyecciones
    sexo_dist = d.get("sexo")            # {"hombre": n, "mujer": n}
    if not edad_dist: provisional.add("edad")
    if not sexo_dist: provisional.add("sexo")
    ocs = ocupaciones(d, cod)
    sal = d.get("salud_pct", {})
    edad_sexo = d.get("edad_sexo")  # cruce real DANE: edad condicionada al sexo
    for i in range(N_POR_DPTO):
        sexo = (sample_w(list(sexo_dist.items())) if sexo_dist
                else rng.choice(["mujer", "hombre"]))
        if edad_sexo:
            grupo = sample_w(list(edad_sexo[sexo].items()))
            centro = dict(EDADES)[grupo]
        elif edad_dist:
            grupo = sample_w(list(edad_dist.items()))
            centro = dict(EDADES)[grupo]
        else:
            grupo, centro = sample_w([(g, w) for (g, c), w in
                zip(EDADES, [6,7,8,8,8,8,7,7,6,6,6,5,4,3,2,2,1,1])]), None
            centro = dict(EDADES)[grupo]
        edad = max(0, centro + rng.randint(-2, 2))
        nombres = dos.get("nombres_frecuentes", {}).get(sexo) or ["Alex", "Sam"]
        apellidos = dos.get("apellidos") or ["García", "Rodríguez"]
        regimen = (sample_w([("contributivo", sal.get("contributivo", 50)),
                             ("subsidiado", sal.get("subsidiado", 50))])
                   if sal else "sin dato")
        edu = d.get("educacion_pct")
        educacion = (sample_w(list(edu.items())) if edu and edad >= 18 else
                     "en el colegio" if 6 <= edad < 18 else "primera infancia")
        residents.append({
            "id": f"{cod}-{i:03d}", "dpto": cod, "dpto_nombre": d["nombre"],
            "nombre": f"{rng.choice(nombres)} {rng.choice(apellidos)}",
            "sexo": sexo, "edad": edad, "grupo_edad": grupo,
            "regimen_salud": regimen, "educacion": educacion,
            "ocupacion": (rng.choice(ocs) if edad >= 18 else
                          "estudiante" if edad >= 6 else "niño(a) de casa"),
        })

# ── validación determinista: sintético vs marginal real ──
val = {"n": len(residents), "por_dpto": N_POR_DPTO,
       "bloques_provisionales": sorted(provisional), "errores": {}}
for cod, d in M.items():
    mine = [r for r in residents if r["dpto"] == cod]
    err = {}
    if d.get("salud_pct"):
        got = sum(r["regimen_salud"] == "contributivo" for r in mine) / len(mine) * 100
        err["salud_contributivo_pp"] = round(abs(got - d["salud_pct"]["contributivo"]), 1)
    if d.get("sexo"):
        tot = sum(d["sexo"].values())
        got = sum(r["sexo"] == "mujer" for r in mine) / len(mine) * 100
        err["sexo_mujer_pp"] = round(abs(got - d["sexo"]["mujer"] / tot * 100), 1)
    if d.get("edad"):
        tot = sum(d["edad"].values())
        got = Counter(r["grupo_edad"] for r in mine)
        err["edad_mae_pp"] = round(sum(
            abs(got.get(g, 0) / len(mine) * 100 - n / tot * 100)
            for g, n in d["edad"].items()) / len(d["edad"]), 2)
    val["errores"][cod] = err

json.dump(residents, (DASH / "residents.json").open("w"), ensure_ascii=False)
json.dump(val, (DASH / "validacion.json").open("w"), ensure_ascii=False, indent=1)
print(f"{len(residents)} residentes de {len(M)} dptos → {DASH}/residents.json")
print(f"provisionales: {sorted(provisional) or 'ninguno'} · validación → validacion.json")
