#!/usr/bin/env python3
"""Banco de preguntas de la ECP 2023 para anclar voces por recuperación.

Diagnóstico que lo motiva (docs/METODO.md): los LLM traen la creencia de que en
Colombia nada funciona, y no la corrigen infiriendo desde actitudes cercanas;
pero sí adoptan una postura dicha explícitamente (39 de 39). Así que cuando
alguien pregunta algo que el DANE midió, se busca la pregunta más parecida y
cada voz recibe lo que SU donante real respondió a ella.

  uv run python scripts/experimento/banco_ecp.py   → web/banco_ecp.json
"""
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def limpiar(t, cat=None):
    t = re.sub(r"^\s*\d+\s*\.\s*", "", t or "")
    # la tarjeta de opciones empieza con "1 <etiqueta de la opción 1>"; cortar
    # por ahí y no por el primer "1", que en las escalas está en el enunciado
    uno = (cat or {}).get("1")
    i = t.find(f" 1 {uno}") if uno else -1
    if i < 0 and uno:
        i = t.find(f" 1. {uno}")
    t = t[:i] if i > 0 else re.sub(r"\s+1\s+S[ií]\s+2\s+No\b.*$", "", t, flags=re.S)
    t = re.sub(r":\s*([a-z])\s*\.\s*", ": ", t)             # sub-letra "a."
    t = re.sub(r"\s+", " ", t).strip(" ?¿")
    return t


def main():
    cb = json.loads((RAIZ / "simcolombia/data/ecp2023_codebook.json").read_text())
    arch = cb["archivos"]
    demo = next((v for k, v in (arch.items() if isinstance(arch, dict) else enumerate(arch))
                 if "democracia" in json.dumps(v)[:400].lower()), None)
    banco = []

    def w(o):
        if isinstance(o, dict):
            c, cat = o.get("codigo"), o.get("categorias")
            t = o.get("texto_literal") or o.get("etiqueta")
            if c and isinstance(cat, dict) and 2 <= len([k for k in cat if k != "99"]) <= 7 and t:
                u = (o.get("universo") or "").lower()
                if "18" in u or not u:
                    txt = limpiar(t, cat)
                    if len(txt) > 15:
                        banco.append({"codigo": c, "texto": txt,
                                      "opciones": {k: v for k, v in cat.items() if k != "99"}})
            for v in o.values():
                w(v)
        elif isinstance(o, list):
            for v in o:
                w(v)

    w(arch)
    # solo preguntas que existen como columna en el módulo de democracia: es de
    # donde salen las respuestas de los donantes
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    import careo_ecp as C
    columnas = set(C.cargar("ecp2023_democracia.zip").columns)
    banco[:] = [b for b in banco if b["codigo"] in columnas]
    vistos, unico = set(), []
    for b in banco:
        if b["codigo"] not in vistos:
            vistos.add(b["codigo"])
            unico.append(b)
    (RAIZ / "web" / "banco_ecp.json").write_text(json.dumps(unico, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(unico)} preguntas en el banco")
    for b in unico[:4]:
        print("  ", b["codigo"], "·", b["texto"][:90], "·", list(b["opciones"].values())[:3])


if __name__ == "__main__":
    main()
