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

import os
SUFIJO = os.environ.get("SIM_SUFIJO", "")
ANIO = int(os.environ.get("SIM_ANIO", os.environ.get("AÑO_SIM", "2026")))
DESPLAZAMIENTO = ANIO - 2026  # años de escenario: la pila envejece y el banco de nombres se desplaza igual
M = json.loads((BASE / "data" / f"marginals{SUFIJO}.json").read_text())["departamentos"]
DOSSIERS = {}
ddir = BASE / "data" / "dossiers"
AVISOS = []
if ddir.exists():
    dfs = sorted(ddir.glob(f"dossier_*{SUFIJO}.json"))
    if not dfs and SUFIJO:
        # escenario sin dossiers propios: hereda los culturales base (efecto de
        # composición: misma cultura, pirámide distinta) y lo deja registrado
        dfs = sorted(ddir.glob("dossier_*.json"))
        AVISOS.append(f"dossiers: no hay dossier_*{SUFIJO}.json; se heredan los base (composición)")
    for f in dfs:
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

# ── Banco nacional de nombres POR GENERACIÓN (realismo de pila colombiana) ──
NOMBRES = {
 "mujer": {
  "mayor": ["Carmen","Blanca","Rosa","Ana","Gloria","Cecilia","Myriam","Teresa",
    "Lucía","Inés","Fanny","Stella","Ligia","Alba","Nubia","Elvia","Graciela",
    "Aura","Mercedes","Josefina","Bertha","Amparo","Leonor","Edilma","Omaira"],
  "adulta": ["Sandra","Patricia","Claudia","Martha","Luz","Diana","Adriana",
    "Mónica","Yolanda","Esperanza","Marcela","Paola","Carolina","Liliana",
    "Johanna","Yaneth","Milena","Amanda","Nancy","Doris","Consuelo","Pilar",
    "Yadira","Rocío","Maritza","Zoraida","Yesenia","Katherine","Viviana","Erika"],
  "joven": ["Camila","Valentina","Daniela","Laura","Alejandra","Natalia","Karen",
    "Angie","Paula","Juliana","Gabriela","Isabella","Mariana","Sara","Luisa",
    "Manuela","Salomé","Danna","Valeria","Sofía","Nicoll","Dayana","Michelle"],
  "nina": ["Emma","Luciana","Antonella","Emily","Samantha","Guadalupe","Celeste",
    "Amelia","Julieta","Violeta","Maité","Alaia"]},
 "hombre": {
  "mayor": ["José","Luis","Jorge","Pedro","Rafael","Gustavo","Hernando","Álvaro",
    "Jaime","Humberto","Gilberto","Marco","Alfonso","Ramiro","Guillermo","Ernesto",
    "Aníbal","Efraín","Gonzalo","Reinaldo","Campo Elías","Misael","Belisario"],
  "adulto": ["Carlos","Juan","Andrés","Fernando","Óscar","Mauricio","Javier",
    "Wilson","Fredy","Édgar","Fabián","Henry","Nelson","Jhon","Alexander",
    "Leonardo","Ricardo","Diego","Iván","Milton","Norbey","Arley","Wilmer",
    "Yeison","Duván","Éder","Robinson","Hugo","Elkin","Julián"],
  "joven": ["Santiago","Sebastián","Nicolás","Samuel","Mateo","Daniel","David",
    "Felipe","Miguel","Cristian","Brayan","Kevin","Esteban","Tomás","Emmanuel",
    "Juan José","Alejandro","Simón","Jerónimo","Dilan","Stiven","Camilo"],
  "nino": ["Matías","Thiago","Liam","Emiliano","Maximiliano","Salvador","Gael",
    "Benjamín","Josué","Ian","Dylan","Martín"]},
}
COMPUESTOS = {"mujer": ["María","Ana","Luz","Leidy","Ingrid","Lina"],
              "hombre": ["Juan","Luis","Carlos","José","Jhon","Miguel"]}
APELLIDOS = ["Rodríguez","Martínez","García","López","González","Hernández",
 "Sánchez","Ramírez","Pérez","Díaz","Muñoz","Rojas","Moreno","Jiménez","Gutiérrez",
 "Torres","Vargas","Castro","Ruiz","Álvarez","Romero","Suárez","Gómez","Ortiz",
 "Cárdenas","Guerrero","Rincón","Castillo","Mejía","Restrepo","Valencia","Ospina",
 "Cardona","Zapata","Montoya","Arias","Betancur","Agudelo","Giraldo","Salazar",
 "Palacios","Mosquera","Córdoba","Machado","Julio","De la Hoz","Barrios","Pacheco",
 "Fontalvo","Cantillo","Navarro","Meza","Acosta","Padilla","Bolaños","Chamorro",
 "Delgado","Ceballos","Paz","Riascos","Quintero","Henao","Uribe","Vélez","Parra",
 "Prieto","Bonilla","Cortés","Reyes","Molina","Camacho","Contreras","Silva"]

def cohorte(edad, sexo):
    key = ("mayor" if edad >= 60 else "adulta" if edad >= 30 else
           "joven" if edad >= 13 else "nina")
    if sexo == "hombre":
        key = {"adulta": "adulto", "nina": "nino"}.get(key, key)
    return NOMBRES[sexo][key]

def nombre_pila(edad, sexo, regionales):
    # el banco de nombres está indexado por edad EN 2026: se reindexa a cohorte de nacimiento
    edad_cohorte = max(0, edad - DESPLAZAMIENTO)
    # 15% toque regional del dossier (si es un nombre normal), 85% banco nacional
    if regionales and rng.random() < 0.15:
        cand = rng.choice(regionales)
        if cand.isalpha() and len(cand) <= 11:
            return cand
    base = rng.choice(cohorte(edad_cohorte, sexo))
    if edad >= 13 and rng.random() < 0.33:  # compuestos: María Fernanda, Luis Alberto
        pre = rng.choice(COMPUESTOS[sexo])
        if pre != base and not base.count(" "):
            return f"{pre} {base}"
    return base


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


REQUIERE_EDAD = {  # oficios con título/carrera: edad mínima creíble
    "docente": 23, "profesor": 23, "funcionario": 22, "contador": 23,
    "abogad": 24, "médic": 25, "enfermer": 22, "universi": 23, "bancari": 20,
}
def elegir_oficio(edad, ocs, rng):
    if edad < 6: return "niño(a) de casa"
    if edad < 18: return "estudiante"
    if edad >= 66:
        return rng.choice(["pensionado(a)", "pensionado(a)", "del hogar", rng.choice(ocs)])
    for _ in range(8):
        o = rng.choice(ocs)
        minimo = next((v for k, v in REQUIERE_EDAD.items() if k in o.lower()), 18)
        if edad >= minimo: return o
    return "trabajador(a) independiente"

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
        # edad uniforme DENTRO del grupo muestreado (sin fugas entre bins)
        lo = int(grupo.split("-")[0]) if "-" in grupo else 85
        hi = int(grupo.split("-")[1]) if "-" in grupo else 94
        edad = rng.randint(lo, hi)
        regionales = dos.get("nombres_frecuentes", {}).get(sexo) or []
        apellidos = APELLIDOS + (dos.get("apellidos") or [])[:6]
        regimen = (sample_w([("contributivo", sal.get("contributivo", 50)),
                             ("subsidiado", sal.get("subsidiado", 50))])
                   if sal else "sin dato")
        edu = d.get("educacion_pct")
        educacion = (sample_w(list(edu.items())) if edu and edad >= 18 else
                     "en el colegio" if 6 <= edad < 18 else "primera infancia")
        residents.append({
            "id": f"{cod}-{i:03d}", "dpto": cod, "dpto_nombre": d["nombre"],
            "nombre": f"{nombre_pila(edad, sexo, regionales)} {rng.choice(apellidos)} {rng.choice(apellidos)}",
            "sexo": sexo, "edad": edad, "grupo_edad": grupo,
            "regimen_salud": regimen, "educacion": educacion,
            "ocupacion": elegir_oficio(edad, ocs, rng),
        })

# ── validación determinista: sintético vs marginal real ──
val = {"n": len(residents), "por_dpto": N_POR_DPTO,
       "bloques_provisionales": sorted(provisional), "avisos": AVISOS, "errores": {}}
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

json.dump(residents, (DASH / f"residents{SUFIJO}.json").open("w"), ensure_ascii=False)
json.dump(val, (DASH / f"validacion{SUFIJO}.json").open("w"), ensure_ascii=False, indent=1)
print(f"{len(residents)} residentes de {len(M)} dptos → {DASH}/residents{SUFIJO}.json")
print(f"provisionales: {sorted(provisional) or 'ninguno'} · validación → validacion{SUFIJO}.json")
