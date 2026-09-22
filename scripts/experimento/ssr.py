#!/usr/bin/env python3
"""SSR — Semantic Similarity Rating: la escala se reconstruye, no se pregunta.

El problema medido en esta casa: cuando le pides a un modelo que escoja un
número del 1 al 5, colapsa hacia el más probable. GLM llegó a poner el 56.6% de
las voces en una sola opción donde los colombianos reales ponen el 17.0%. Y no
se arregla con el termómetro 0-100: medimos que empeora (W1 0.084 → 0.154).

La salida que reporta la literatura de 2026 es no preguntar la escala. La
persona habla con sus palabras, y la escala se reconstruye midiendo a qué punto
de anclaje se parece semánticamente lo que dijo. Lo importante es el último
paso: de cada persona NO se toma el anclaje más parecido —eso sería volver a
colapsar— sino la distribución completa de parecidos. La dispersión se recupera
porque se deja de tirar información.

  Correcting Mode Collapse in Silicon Sampling with Semantic Similarity Rating
  arXiv:2607.28550 — reportan divergencia KL de 0.61 a 0.13 en DeepSeek.

Uso:
  uv run --with pyreadstat --with pandas --python 3.12 python \\
     scripts/experimento/ssr.py <archivo_modo_libre.json> [--temp 0.25]
"""
import json
import math
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import careo_ecp as C  # noqa: E402  — la verdad del DANE vive ahí, no se duplica

RAIZ = Path(__file__).resolve().parents[2]
MODELO_EMB = os.environ.get("MODELO_EMB", "openai/text-embedding-3-small")
TEMPERATURA = 0.25   # el valor que minimiza KL en el paper; se puede barrer

# Los anclajes son el corazón del método: describen cada punto de la escala en
# el castellano en que hablaría la gente, no en el del formulario. Un anclaje
# escrito como enunciado de encuesta se parecería a todas las respuestas por
# igual y el método no distinguiría nada.
ANCLAJES = {
    "satisfaccion": [
        "Estoy muy insatisfecho. Esto no sirve, no funciona nada, estamos peor "
        "que nunca y no veo por dónde mejore.",
        "Estoy insatisfecho. Hay cosas que fallan, uno ve más problemas que "
        "soluciones y eso cansa.",
        "Ni satisfecho ni insatisfecho. Hay cosas buenas y cosas malas, ahí va, "
        "no me quejo pero tampoco celebro.",
        "Estoy satisfecho. En general funciona, uno ve avances, hay cosas por "
        "mejorar pero vamos bien.",
        "Estoy muy satisfecho. Funciona bien, estoy contento con cómo va, no "
        "tengo queja.",
    ],
    "importancia": [
        "No me importa nada, eso me da igual, no sirve para nada.",
        "Me importa poco, no le veo mayor sentido.",
        "Me importa más o menos, ni mucho ni poco.",
        "Me importa, me parece algo valioso.",
        "Me importa muchísimo, para mí es lo más importante de todo.",
    ],
    "acuerdo": [
        "Estoy totalmente en desacuerdo, eso es completamente falso.",
        "Estoy en desacuerdo, no me parece que sea así.",
        "Ni de acuerdo ni en desacuerdo, depende, no sabría decir.",
        "Estoy de acuerdo, me parece que sí es así.",
        "Estoy totalmente de acuerdo, eso es exactamente así.",
    ],
}


def familia_de(texto_pregunta):
    """Qué juego de anclajes le toca a esta pregunta.

    Se decide por el texto de la pregunta del DANE, no a mano: si mañana se
    agrega un ítem nuevo, cae solo en la familia que le corresponde.
    """
    t = (texto_pregunta or "").lower()
    if "satisfech" in t:
        return "satisfaccion"
    if "importan" in t:
        return "importancia"
    return "acuerdo"


def embeber(textos, lote=64):
    """Vectores de OpenRouter. Por lotes, que es una petición en vez de cien."""
    key = None
    for linea in (RAIZ / ".env").read_text().splitlines():
        if linea.startswith("OPENROUTER_API_KEY="):
            key = linea.split("=", 1)[1].strip().strip("\"'")
    if not key:
        sys.exit("⛔ falta OPENROUTER_API_KEY en .env")

    fuera = []
    for i in range(0, len(textos), lote):
        cuerpo = json.dumps({"model": MODELO_EMB,
                             "input": textos[i:i + lote]}).encode()
        req = urllib.request.Request(
            "https://openrouter.ai/api/v1/embeddings", data=cuerpo,
            headers={"Authorization": "Bearer " + key,
                     "Content-Type": "application/json"})
        for intento in range(3):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    d = json.loads(r.read())
                fuera.extend(x["embedding"] for x in
                             sorted(d["data"], key=lambda x: x["index"]))
                break
            except urllib.error.URLError as exc:
                if intento == 2:
                    sys.exit(f"⛔ embeddings: {exc}")
    return fuera


def coseno(a, b):
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def pmf_de(sims, temp):
    """Parecidos → distribución de probabilidad sobre los cinco puntos.

    Min-max primero porque los cosenos entre textos del mismo idioma viven
    todos en una banda estrecha (0.6-0.9): sin reescalar, el softmax los ve
    casi iguales y devuelve una distribución plana que no dice nada.
    """
    lo, hi = min(sims), max(sims)
    norm = [(s - lo) / (hi - lo) if hi > lo else 0.5 for s in sims]
    exp = [math.exp(x / temp) for x in norm]
    tot = sum(exp)
    return [e / tot for e in exp]


def main():
    ruta = Path(sys.argv[1])
    temp = TEMPERATURA
    if "--temp" in sys.argv:
        temp = float(sys.argv[sys.argv.index("--temp") + 1])

    D = json.loads(ruta.read_text())
    if D.get("modo") != "libre":
        sys.exit(f"⛔ este archivo es modo '{D.get('modo')}'. SSR necesita 'libre'.")

    textos = [(r.get("crudo") or "").strip() for r in D["respuestas"]]
    vivos = [i for i, x in enumerate(textos) if len(x) >= 10]
    if not vivos:
        sys.exit("⛔ ninguna respuesta con texto suficiente")

    fam = familia_de(D.get("pregunta"))
    anclas = ANCLAJES[fam]

    print(f"\nSSR — {D['codigo']} · {D.get('modelo', '?')} · "
          f"anclajes «{fam}» · T={temp}")
    print(f"embeddings: {MODELO_EMB} · {len(vivos)} respuestas con texto"
          f"{f' ({len(textos) - len(vivos)} descartadas por vacías)' if len(vivos) < len(textos) else ''}")

    vecs = embeber(anclas + [textos[i] for i in vivos])
    v_anc, v_res = vecs[:5], vecs[5:]

    # Cada persona aporta su distribución completa, no su punto más parecido:
    # quedarse con el máximo sería volver a colapsar, que es el fallo que
    # venimos a arreglar.
    acum = [0.0] * 5
    duros = [0] * 5          # para comparar contra el método que sí colapsa
    for v in v_res:
        pmf = pmf_de([coseno(v, a) for a in v_anc], temp)
        for k in range(5):
            acum[k] += pmf[k]
        duros[pmf.index(max(pmf))] += 1

    p_ssr = {k + 1: acum[k] / len(v_res) for k in range(5)}
    p_duro = {k + 1: duros[k] / len(v_res) for k in range(5)}

    # ── la verdad humana, con el factor de expansión oficial ────────────
    demo = C.cargar("ecp2023_democracia.zip")
    try:
        viv = C.cargar("ecp2023_viviendas.zip")
        fex = next((c for c in viv.columns if c.upper().startswith("FEX")), None)
    except Exception:
        fex = None
    if fex:
        demo = demo.merge(viv[["DIRECTORIO", fex]].drop_duplicates("DIRECTORIO"),
                          on="DIRECTORIO", how="left")
        pesos = demo[fex].fillna(0).tolist()
    else:
        pesos = None
    p_hum, _ = C.distribucion(demo[D["codigo"]].tolist(), pesos)

    # ── el careo ────────────────────────────────────────────────────────
    print()
    print(f"{'opción':<24}{'humanos':>10}{'SSR':>10}{'argmax':>10}")
    print("-" * 54)
    for k in range(1, 6):
        print(f"{k:<24}{100 * p_hum[k]:>9.1f}%{100 * p_ssr[k]:>9.1f}%"
              f"{100 * p_duro[k]:>9.1f}%")
    print("-" * 54)

    mh, sh = C.media_sd(p_hum)
    ms, ss = C.media_sd(p_ssr)
    md, sd = C.media_sd(p_duro)
    print(f"{'media':<24}{mh:>10.2f}{ms:>10.2f}{md:>10.2f}")
    print(f"{'desviación':<24}{sh:>10.2f}{ss:>10.2f}{sd:>10.2f}")
    print(f"{'razón de desviación':<24}{'1.00':>10}{ss / sh:>10.2f}{sd / sh:>10.2f}")

    w_ssr = C.w1_normalizado(p_ssr, p_hum)
    w_duro = C.w1_normalizado(p_duro, p_hum)
    print(f"\n{'W1 normalizado':<24}{'—':>10}{w_ssr:>10.3f}{w_duro:>10.3f}")
    print("\nLa columna «argmax» es lo que pasaría si de cada persona nos "
          "quedáramos\ncon su anclaje más parecido. Está para ver qué aporta "
          "guardar la\ndistribución entera: si SSR no le gana, el método no "
          "está haciendo nada.")


if __name__ == "__main__":
    main()
