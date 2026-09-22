#!/usr/bin/env python3
"""La búsqueda del servidor (api/opina.js, acción recuperar), en Python.

Embeddings proponen las 3 preguntas del banco más parecidas; el juez decide si
alguna pregunta LO MISMO o ninguna. Mismo texto de instrucción que producción:
si cambias uno, cambia el otro.

  uv run python scripts/experimento/recuperar.py <banco.json> <preguntas.json>
    preguntas.json: ["pregunta", ...]  →  imprime y guarda la elección
"""
import concurrent.futures as cf
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import ssr as S  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
INSTR = ("¿Cuál pregunta de la encuesta pregunta ESENCIALMENTE LO MISMO que la persona: "
         "el mismo tema Y el mismo sentido, aunque cambien las palabras? Si solo comparten "
         "palabras o tema general pero preguntan otra cosa, es 'ninguna'.")


def _llave():
    for l in (RAIZ / ".env").read_text().splitlines():
        if l.startswith("OPENROUTER_API_KEY="):
            return l.split("=", 1)[1].strip().strip("\"'")


def juez(q, cands, key):
    L = "ABC"
    crit = {L[i]: f"pregunta lo mismo que «{c['texto'][-120:]}»" for i, c in enumerate(cands)}
    crit["ninguna"] = "ninguna pregunta lo mismo: el tema o el sentido es otro"
    body = {"model": "typesafe/jev-1.13",
            "state": f"Pregunta que escribió una persona: «{q}»\nPreguntas de una encuesta oficial:\n"
                     + "\n".join(f"{L[i]}: {c['texto']}" for i, c in enumerate(cands)),
            "questions": {"igual": {"type": "choice", "criteria": crit, "instructions": INSTR}}}
    req = urllib.request.Request("https://openrouter.ai/api/alpha/decisions",
                                 data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        ch = json.loads(urllib.request.urlopen(req, timeout=60).read())["answers"]["igual"].get("choice")
    except Exception:
        return None                      # ante la duda, sin ancla
    return cands[L.index(ch)] if isinstance(ch, str) and ch in L and L.index(ch) < len(cands) else None


def recuperar(banco, preguntas):
    key = _llave()
    vec = S.embeber([b["texto"] for b in banco] + preguntas)
    vb, vq = vec[:len(banco)], vec[len(banco):]
    tops = [[banco[i] for _, i in sorted(((S.coseno(v, b), i) for i, b in enumerate(vb)), reverse=True)[:3]]
            for v in vq]
    with cf.ThreadPoolExecutor(8) as ex:
        return list(ex.map(lambda z: juez(z[0], z[1], key), zip(preguntas, tops)))


if __name__ == "__main__":
    banco = json.loads(Path(sys.argv[1]).read_text())
    qs = json.loads(Path(sys.argv[2]).read_text())
    el = recuperar(banco, qs)
    for q, e in zip(qs, el):
        print(f"  {(e['codigo'] if e else '— sin ancla'):<18} ← {q[:70]}")
