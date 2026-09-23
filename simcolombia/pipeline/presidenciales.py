#!/usr/bin/env python3
"""Resultados presidenciales 2022 y 2026 por departamento (Registraduría, mesa a mesa)
→ simcolombia/data/presidenciales.json. Solo votos por candidato (sin blanco ni nulos).

  uv run python simcolombia/pipeline/presidenciales.py
"""
import csv, io, json, re, zipfile
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "simcolombia" / "data" / "raw_v2"
# Registraduría → DANE (los códigos de la Registraduría son otros)
REG_DANE = {"01": "05", "03": "08", "05": "13", "07": "15", "09": "17", "11": "19", "12": "20", "13": "23",
    "15": "25", "16": "11", "17": "27", "19": "41", "21": "47", "23": "52", "24": "66", "25": "54", "26": "63",
    "27": "68", "28": "70", "29": "73", "31": "76", "40": "81", "44": "18", "46": "85", "48": "44", "50": "94",
    "52": "50", "54": "95", "56": "88", "60": "91", "64": "86", "68": "97", "72": "99"}


def v2022(nombre):
    """CSV con nombres: DEP;DEPNOMBRE;…;CANNOMBRE;VOTOS."""
    out = defaultdict(lambda: defaultdict(int))
    with zipfile.ZipFile(RAW / nombre) as z, z.open(z.namelist()[0]) as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
            cand = r["CANNOMBRE"].strip()
            if r["DEP"] == "88" or not cand or re.search(r"BLANCO|NULO|NO MARCADO", cand):
                continue
            out[REG_DANE.get(r["DEP"], r["DEP"])][cand] += int(r["VOTOS"])
    return out


def v2026(nombre):
    """ESCRUTINIO.csv sin encabezado: [1]=dpto Registraduría, [10]=candidato, [11]=votos;
    los nombres, en CANDIDATOS_*.TXT dentro del zip de archivos básicos."""
    out = defaultdict(lambda: defaultdict(int))
    with zipfile.ZipFile(RAW / nombre) as z:
        esc = next(n for n in z.namelist() if n.endswith("ESCRUTINIO.csv"))
        basicos = next(n for n in z.namelist() if re.search(r"(?i)archivos ?basicos.*\.zip$", n))
        with zipfile.ZipFile(io.BytesIO(z.read(basicos))) as zb:
            cands = zb.read(next(n for n in zb.namelist() if "CANDIDATOS" in n)).decode("latin-1")
        # "001 0000000000 0026 001 1 NOMBRE": partido en [12:16], candidato en [16:19]
        nombres = {l[16:19]: re.sub(r"\s+", " ", l[20:120]).strip() for l in cands.splitlines() if l.strip()}
        with z.open(esc) as f:
            for row in csv.reader(io.TextIOWrapper(f, encoding="latin-1"), delimiter=";"):
                if len(row) < 12 or row[1] == "88":
                    continue
                nombre = nombres.get(row[10]) or ("_BLANCO_NULO" if row[10] in ("996", "997", "998") else None)
                if nombre:
                    out[REG_DANE.get(row[1], row[1])][nombre] += int(row[11])
    return out


# Familia política de cada candidato de 2026 (primera vuelta): la misma escala de
# 5 familias que usa la voz (LEAN_TXT en web/index.html). Mapeo por partido/coalición.
FAMILIA_2026 = {
    "IVÁN CEPEDA CASTRO": "izquierda", "CARLOS EDUARDO CAICEDO OMAR": "izquierda",
    "ROY LEONARDO BARRERAS MONTEALEGRE": "izquierda",
    "ABELARDO DE LA ESPRIELLA": "derecha_uribismo", "PALOMA VALENCIA LASERNA": "derecha_uribismo",
    "MIGUEL URIBE LONDOÑO": "derecha_uribismo", "GUSTAVO MATAMOROS CAMACHO": "derecha_uribismo",
    "CLAUDIA LÓPEZ": "verdes_alternativos", "SERGIO FAJARDO VALDERRAMA": "verdes_alternativos",
    "LUIS GILBERTO MURILLO URRUTIA": "verdes_alternativos", "SONDRA MACOLLINS GARVIN PINTO": "verdes_alternativos",
    "ÓSCAR MAURICIO LIZCANO ARANGO": "centro_tradicional", "RAÚL SANTIAGO BOTERO JARAMILLO": "centro_tradicional",
    "_BLANCO_NULO": "otros_blanco_nulo",
}


def familias(d):
    """Votos de la primera vuelta 2026 → % por familia (blanco y nulos cuentan)."""
    f = defaultdict(int)
    for cand, v in d.items():
        f[FAMILIA_2026.get(cand, "otros_blanco_nulo")] += v
    t = sum(f.values()) or 1
    return {k: round(100 * v / t, 1) for k, v in sorted(f.items(), key=lambda x: -x[1])}


def habilitados_2026(nombre):
    """Censo electoral 2026 por departamento (DANE): DIVIPOL de los archivos básicos,
    bloque numérico en la columna 91: [1:9] mujeres, [9:17] hombres habilitados."""
    t = defaultdict(int)
    with zipfile.ZipFile(RAW / nombre) as z:
        basicos = next(n for n in z.namelist() if re.search(r"(?i)archivos ?basicos.*\.zip$", n))
        with zipfile.ZipFile(io.BytesIO(z.read(basicos))) as zb:
            div = zb.read(next(n for n in zb.namelist() if "DIVIPOL" in n)).decode("latin-1")
    for l in div.splitlines():
        b = l[91:116]
        if b[:17].isdigit() and l[:2] != "88":
            t[REG_DANE.get(l[:2], l[:2])] += int(b[1:9]) + int(b[9:17])
    return t


def con_abstencion(fam, votos, habil):
    """Familias sobre TODOS los adultos habilitados: quien no votó va a 'ninguno'."""
    part = votos / habil if habil else 1
    f = {k: v * part for k, v in fam.items()}
    f["otros_blanco_nulo"] = f.get("otros_blanco_nulo", 0) + 100 * (1 - part)
    return {k: round(v, 1) for k, v in sorted(f.items(), key=lambda x: -x[1])}


def pct(d):
    d = {k: v for k, v in d.items() if k != "_BLANCO_NULO"}   # % entre candidatos
    t = sum(d.values()) or 1
    return {k: round(100 * v / t, 1) for k, v in sorted(d.items(), key=lambda x: -x[1])}


def main():
    res = {}
    for clave, fn, lector in [("2022_1v", "pres2022_1v.zip", v2022), ("2022_2v", "pres2022_2v.zip", v2022),
                              ("2026_1v", "pres2026_1v.zip", v2026), ("2026_2v", "pres2026_2v.zip", v2026)]:
        d = lector(fn)
        nac = defaultdict(int)
        for dep in d.values():
            for k, v in dep.items():
                nac[k] += v
        res[clave] = {"nacional": pct(nac), **{dep: pct(v) for dep, v in d.items()}}
        if clave == "2026_1v":
            hab = habilitados_2026(fn)
            hab["nacional"] = sum(hab.values())
            todos = {"nacional": nac, **d}
            res["lean_2026"] = {k: familias(v) for k, v in todos.items()}
            res["lean_2026"]["fuente"] = "Registraduría, presidencial 2026 primera vuelta (solo votantes)"
            res["lean_2026_adultos"] = {k: con_abstencion(familias(v), sum(v.values()), hab.get(k, 0)) for k, v in todos.items()}
            res["lean_2026_adultos"]["fuente"] = "igual, sobre el censo electoral: quien no votó cuenta como 'ninguno'"
            res["participacion_2026_1v"] = {k: round(100 * sum(v.values()) / hab[k], 1) for k, v in todos.items() if hab.get(k)}
        print(clave, "Sucre:", list(res[clave]["70"].items())[:4], "· nacional:", list(res[clave]["nacional"].items())[:3])
    print("lean_2026 Sucre:", res["lean_2026"]["70"], "· nacional:", res["lean_2026"]["nacional"])
    print("lean_2026_adultos Sucre:", res["lean_2026_adultos"]["70"], "· participación", res["participacion_2026_1v"]["70"], "% (nacional", res["participacion_2026_1v"]["nacional"], "%)")
    # web/inclinacion.json: cuánto más a la izquierda (+) o a la derecha (−) votó cada
    # departamento que el país en la primera vuelta de 2026 (izquierda − derecha, puntos).
    # La usa el sondeo sin ancla: la estimación nacional se corre k·inclinación según
    # el departamento de cada voz, solo si la pregunta es partidista (medido: 2018 y 2022).
    L = res["lean_2026"]; n = L["nacional"]
    incl = {d: round((v.get("izquierda", 0) - v.get("derecha_uribismo", 0)) - (n.get("izquierda", 0) - n.get("derecha_uribismo", 0)), 1)
            for d, v in L.items() if d not in ("nacional", "fuente")}
    (RAIZ / "web" / "inclinacion.json").write_text(json.dumps({"k": 0.5, "fuente": "Registraduría, presidencial 2026 primera vuelta",
        "dptos": incl}, ensure_ascii=False, separators=(",", ":")))
    (RAIZ / "simcolombia" / "data" / "presidenciales.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
