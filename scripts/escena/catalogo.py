#!/usr/bin/env python3
"""Instala personajes y utilería en web/ y escribe web/gente/catalogo.json.

  uv run python scripts/escena/catalogo.py <carpeta_tiras> <carpeta_utileria_recortada>

catalogo.json: {"gente": [{id, s: H|M, e: edad, r: [regiones], o: oficio}],
                "utileria": {region: {"mesa": archivo, "cosas": [archivos]}}}
Las regiones son las 12 del reparto (scripts/escena/reparto/). A cada
residente el sitio le busca el personaje más parecido: es vestuario, no dato.
OJO: la utilería que escribe esto es automática; la desplegada se curó a mano
(una mesa por región, solo objetos que se sostienen solos) y vive en el
catalogo.json publicado. Si regeneras, vuelve a curarla. Igual los personajes
con un mueble pegado (carretilla, mostrador): "fijo":1, no se asignan.
Los sucre__* (9, hechos a mano con GPT Image) llevan "dp":"70": se prefieren para
los residentes de Sucre. Si regeneras, consérvalos.
Modelo para lo nuevo: openai/gpt-image-2.5-flare, quality low, background
transparent, input_references (≈$0.005 la hoja; ver banco_imagen.mjs).
"""
import json
import re
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

RAIZ = Path(__file__).resolve().parents[2]
GENTE, ESC = RAIZ / "web" / "gente", RAIZ / "web" / "escenas"
ANDES = ["bogota", "antioquia", "santander", "cafetero", "boyaca", "sur_andino"]
TODAS = ANDES + ["caribe", "caribe_rural", "pacifico", "llanos", "amazonia", "insular_guajira"]
URBANAS = ANDES + ["caribe", "pacifico", "llanos"]
# los 47 personajes de la primera tanda: [sexo, edad, regiones, oficio]
VIEJOS = {
    "andino_0": ["H", 24, ANDES, "estudiante"], "andino_1": ["M", 22, ANDES, "estudiante"],
    "andino_2": ["H", 40, ANDES, "oficinista"], "andino_3": ["M", 40, ANDES, "oficinista profesional"],
    "andino_4": ["H", 70, ANDES, "pensionado"], "andino_5": ["M", 70, ANDES, "ama de casa"],
    "andino_6": ["H", 38, TODAS, "obrero de construcción"], "andino_7": ["H", 24, URBANAS, "domiciliario"],
    "campo_0": ["H", 26, ["cafetero", "antioquia", "santander"], "agricultor cafetero"],
    "campo_1": ["M", 26, ["cafetero", "antioquia"], "recolectora de café"],
    "campo_2": ["H", 45, ["boyaca", "sur_andino", "cafetero"], "agricultor"],
    "campo_3": ["M", 45, ["boyaca", "sur_andino"], "agricultora"],
    "campo_4": ["H", 72, ["boyaca", "sur_andino", "santander"], "agricultor"],
    "campo_5": ["M", 72, ["boyaca", "sur_andino", "cafetero"], "ama de casa"],
    "campo_6": ["H", 45, ["antioquia", "cafetero", "llanos"], "arriero ganadero"],
    "campo_7": ["M", 45, ANDES, "tendera comerciante"],
    "caribe_0": ["H", 24, ["caribe", "caribe_rural"], "estudiante"], "caribe_1": ["M", 24, ["caribe", "caribe_rural"], "estudiante"],
    "caribe_2": ["H", 45, ["caribe", "caribe_rural"], "comerciante"], "caribe_3": ["M", 45, ["caribe", "pacifico"], "vendedora"],
    "caribe_4": ["H", 68, ["caribe", "caribe_rural"], "pescador"], "caribe_5": ["M", 70, ["caribe", "caribe_rural"], "ama de casa"],
    "caribe_6": ["H", 35, ["caribe", "caribe_rural"], "mototaxista conductor"], "caribe_7": ["H", 40, ["caribe", "caribe_rural"], "mototaxista conductor"],
    "oriente_0": ["H", 45, ["llanos"], "ganadero"], "oriente_1": ["M", 35, ["llanos"], "comerciante"],
    "oriente_2": ["H", 24, ["llanos", "cafetero"], "jornalero agricultor"], "oriente_3": ["M", 40, ["insular_guajira"], "artesana"],
    "oriente_4": ["H", 45, ["insular_guajira"], "pastor comerciante"], "oriente_5": ["H", 40, ["amazonia"], "pescador agricultor"],
    "oriente_6": ["M", 40, ["amazonia"], "agricultora artesana"], "oriente_7": ["H", 70, ["llanos"], "ganadero"],
    "pacifico_0": ["H", 22, ["pacifico"], "estudiante"], "pacifico_1": ["M", 22, ["pacifico"], "estudiante"],
    "pacifico_2": ["H", 42, ["pacifico"], "pescador"], "pacifico_3": ["M", 42, ["pacifico"], "cantadora comerciante"],
    "pacifico_4": ["H", 70, ["pacifico"], "pensionado"], "pacifico_5": ["M", 70, ["pacifico"], "ama de casa"],
    "pacifico_6": ["M", 38, TODAS, "enfermera auxiliar de salud"], "pacifico_7": ["H", 42, ["pacifico"], "agricultor"],
    "urbano_0": ["H", 50, URBANAS, "taxista conductor"], "urbano_1": ["M", 22, URBANAS, "estudiante"],
    "urbano_2": ["H", 40, TODAS, "vigilante de seguridad"], "urbano_3": ["M", 40, TODAS, "ama de casa hogar"],
    "urbano_4": ["H", 72, URBANAS, "pensionado"], "urbano_5": ["M", 45, URBANAS, "vendedora ambulante"],
    "urbano_6": ["H", 26, URBANAS, "programador técnico"],
}


def cuadrado(f):
    """¿La pieza vino con su propio fondo (un cuadro) en vez de recortada?"""
    a = np.array(Image.open(f).convert("RGBA"))[..., 3] > 0
    return a.mean() > .9


def main(tiras, util):
    tiras, util = Path(tiras), Path(util)
    GENTE.mkdir(exist_ok=True)
    for f in GENTE.glob("*.webp"):
        f.unlink()
    nuevos = {}
    for f in (RAIZ / "scripts" / "escena" / "reparto").glob("reparto_*.json"):
        reg = f.stem[8:]
        d = json.loads(re.search(r"\{.*\}", f.read_text(), re.S).group(0))
        for p in d["personajes"]:
            pid = f"{reg}__{p['id']}".lower()
            pid = re.sub(r"[^a-z0-9_]", "", pid)
            nuevos[pid] = [p["sexo"], int(p["edad"]), [reg], p["oficio"].lower()]
    gente = []
    for f in sorted(tiras.glob("*_poses.webp")):
        pid = f.name[:-11]
        meta = VIEJOS.get(pid) or nuevos.get(pid)
        if pid == "urbano_7":                      # el presentador del show
            meta = ["H", 50, [], "presentador"]
        if not meta:
            print("sin metadatos:", pid)
            continue
        shutil.copy(f, GENTE / f.name)
        shutil.copy(tiras / f"{pid}.webp", GENTE / f"{pid}.webp")
        s, e, r, o = meta
        gente.append({"id": pid, "s": s, "e": e, "r": r, "o": o})
    utileria = {}
    for f in sorted(util.glob("*_0.webp")):
        reg = f.name[:-7]
        mesa = f"mesa_{reg}.webp"
        shutil.copy(f, ESC / mesa)
        cosas = []
        for k in range(1, 5):
            g = util / f"{reg}_{k}.webp"
            if g.exists() and not cuadrado(g):
                shutil.copy(g, ESC / f"cosa_{reg}_{k}.webp")
                cosas.append(f"cosa_{reg}_{k}.webp")
        utileria[reg] = {"mesa": mesa, "cosas": cosas}
    (GENTE / "catalogo.json").write_text(json.dumps({"gente": gente, "utileria": utileria}, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(gente)} personajes · utilería de {len(utileria)} regiones, "
          f"{sum(len(u['cosas']) for u in utileria.values())} cosas limpias")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
