#!/usr/bin/env python3
"""Actitudes reales para las personas sintéticas: un donante de la ECP 2023.

El modelo trae de fábrica una creencia sobre Colombia: medido, sin ninguna
persona responde "no" al 100% a "¿se garantiza la igualdad ante la ley?",
cuando los colombianos dicen sí el 41%. La persona no lo arregla, porque el
sesgo no está en ella sino en el modelo.

Aquí cada persona sintética (que ya es una persona real de la GEIH) recibe las
respuestas de un encuestado real de la ECP de su misma región, sexo, edad y
educación: su confianza en 15 instituciones y su satisfacción con la
democracia. Es el "conjunto A" de la transferencia entre encuestas (Ku et al.
2026, arXiv:2607.03091): se le da al modelo lo que la persona respondió en un
tema, y se mide si acierta en preguntas que nunca vio.

Donante elegido al azar dentro de la celda, con probabilidad proporcional al
factor de expansión, y de forma determinista por el id del residente.

  uv run python simcolombia/pipeline/donantes_ecp.py      → web/actitudes.json
"""
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts" / "experimento"))
import careo_ecp as C  # noqa: E402  lectura de los .sav del DANE

ITEMS = [f"P5263S{i}" for i in range(1, 16)] + ["P5301"]
# Hermanas: respuestas del donante a OTRAS preguntas de las mismas baterías
# (derechos garantizados, requisitos de la democracia). Son contexto, como el
# conjunto A del paper. Disjuntas de EVAL: ninguna pregunta que se mide aquí.
HERMANAS = ["P5304S1", "P5304S3", "P5304S4", "P5304S9", "P5306S4", "P5306S5",
            "P5306S6", "P5317S1", "P5317S3", "P5317S4", "P5317S10"]
# preguntas de prueba: NUNCA van a la voz; se guardan aparte para evaluar
EVAL = ["P5304S6", "P5306S2", "P5317S7", "P5302", "P5261S8", "P5261S4",
        "P5304S2", "P5304S5", "P5304S10", "P5306S1", "P5306S3", "P5306S7", "P5317S2", "P5317S8"]
LLAVES = ["DIRECTORIO", "NRO_ENCUESTA", "HOGAR_NUMERO", "PERSONA_NUMERO"]

# Regiones de la ECP (1 Bogotá · 2 Caribe · 3 Oriental · 4 Central · 5 Pacífica).
# Orinoquía y Amazonía no tienen región propia en la ECP: van a la vecina.
# Es una aproximación, declarada.
REGION = {
    "11": 1,
    "08": 2, "13": 2, "20": 2, "23": 2, "44": 2, "47": 2, "70": 2, "88": 2,
    "15": 3, "25": 3, "50": 3, "54": 3, "68": 3, "81": 3, "85": 3, "99": 3, "94": 3,
    "05": 4, "17": 4, "18": 4, "41": 4, "63": 4, "66": 4, "73": 4, "86": 4, "91": 4, "95": 4, "97": 4,
    "19": 5, "27": 5, "52": 5, "76": 5,
}


def grupo_edad(e):
    return 0 if e < 30 else 1 if e < 45 else 2 if e < 60 else 3


def grupo_edu_ecp(c):
    return 0 if c <= 3 else 1 if c <= 5 else 2          # ninguno-primaria · secundaria-media · superior


def grupo_edu_res(e):
    return {"ninguna": 0, "primaria": 0, "secundaria": 1, "media": 1, "superior": 2}.get(e, 1)


def main():
    demo = C.cargar("ecp2023_democracia.zip")
    car = C.cargar("ecp2023_caracteristicas.zip")
    viv = C.cargar("ecp2023_viviendas.zip")
    df = demo.merge(car[LLAVES + ["P220", "P5785", "P6210"]], on=LLAVES, how="inner")
    df = df.merge(viv[["DIRECTORIO", "REGION", "FEX_P"]].drop_duplicates("DIRECTORIO"),
                  on="DIRECTORIO", how="left")
    df = df[(df["P5785"] >= 18) & df["P6210"].between(1, 7) & df["REGION"].notna()]

    celdas = defaultdict(list)
    for _, f in df.iterrows():
        resp = [None if (f[i] != f[i] or int(f[i]) == 99) else int(f[i]) for i in ITEMS]
        if sum(x is not None for x in resp) < 8:
            continue                                     # donante con muy poca información
        clave = (int(f["REGION"]), int(f["P220"]), grupo_edad(f["P5785"]), grupo_edu_ecp(int(f["P6210"])))
        ev = [None if (f[i] != f[i] or int(f[i]) == 99) else int(f[i]) for i in EVAL]
        he = [None if (f[i] != f[i] or int(f[i]) == 99) else int(f[i]) for i in HERMANAS]
        celdas[clave].append((float(f["FEX_P"] or 0), resp, ev, he))

    def elegir(cands, semilla):
        tot = sum(c[0] for c in cands)
        x = (int(hashlib.sha256(semilla.encode()).hexdigest(), 16) % 10**9) / 10**9 * tot
        for c in cands:
            x -= c[0]
            if x <= 0:
                return c
        return cands[-1]

    res = json.loads((RAIZ / "web" / "residents_v2.json").read_text())
    res = res if isinstance(res, list) else res.get("residentes")
    por_id, evaluacion, hermanas, nivel = {}, {}, {}, defaultdict(int)
    for r in res:
        if r["edad"] < 18:
            continue
        reg = REGION.get(r["dpto"])
        sx = 1 if r["sexo"] == "hombre" else 2
        ge, gu = grupo_edad(r["edad"]), grupo_edu_res(r["educacion"])
        # de la celda más fina a la más gruesa: nunca sin donante
        for i, clave in enumerate([(reg, sx, ge, gu), (reg, sx, ge, None), (reg, None, ge, None), (reg, None, None, None)]):
            cands = [c for k, v in celdas.items() if all(a is None or a == b for a, b in zip(clave, k)) for c in v]
            if len(cands) >= 5:
                _, a, ev, he = elegir(cands, r["id"])
                por_id[r["id"]], evaluacion[r["id"]], hermanas[r["id"]] = a, ev, he
                nivel[i] += 1
                break

    salida = {"fuente": "ECP 2023 del DANE, donante emparejado por región, sexo, edad y educación",
              "items": ITEMS, "por_id": por_id,
              "hermanas_items": HERMANAS, "hermanas": hermanas}
    (RAIZ / "web" / "actitudes.json").write_text(json.dumps(salida, separators=(",", ":")))
    # fuera de web/ a propósito: son respuestas que la voz no debe ver nunca
    (RAIZ / "scripts" / "experimento" / "donantes_eval.json").write_text(
        json.dumps({"items": EVAL, "por_id": evaluacion}, separators=(",", ":")))
    n = sum(nivel.values())
    print(f"{n} adultos con donante · {len(celdas)} celdas con datos")
    for i, et in enumerate(["región·sexo·edad·educación", "sin educación", "solo región·edad", "solo región"]):
        print(f"  {et:<28} {nivel[i]:>5}  ({100*nivel[i]/n:.1f}%)")


if __name__ == "__main__":
    main()
