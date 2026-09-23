#!/usr/bin/env python3
"""Lee los bugs que propuso el enjambre (runs/<corrida>/artifacts/*.json) y
dice cuáles se pueden aplicar tal cual: el fragmento "buscar" tiene que
existir UNA sola vez en el archivo. No aplica nada: eso lo decide quien revisa.

  uv run python scripts/verificar_bugs.py runs/<corrida>          # tabla
  uv run python scripts/verificar_bugs.py runs/<corrida> --json   # para revisar uno a uno
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def cargar(f):
    t = f.read_text()
    t = re.sub(r"^```\w*|```$", "", t.strip(), flags=re.M)
    m = re.search(r"\{.*\}", t, re.S)
    try:
        return json.loads(m.group(0)).get("bugs", []) if m else []
    except json.JSONDecodeError:
        return None


def main(run, como_json):
    todos = []
    for f in sorted((Path(run) / "artifacts").glob("*.json")):
        bugs = cargar(f)
        if bugs is None:
            print(f"{f.name}: JSON inválido", file=sys.stderr); continue
        for b in bugs:
            arch = RAIZ / b.get("archivo", "")
            texto = arch.read_text() if arch.is_file() else ""
            n = texto.count(b.get("buscar", "\0")) if b.get("buscar") else 0
            b["_agente"], b["_coincide"] = f.stem, n
            todos.append(b)
    if como_json:
        print(json.dumps(todos, ensure_ascii=False, indent=1)); return
    for b in todos:
        ok = "✓" if b["_coincide"] == 1 else ("✗ 0" if b["_coincide"] == 0 else f"✗ {b['_coincide']}")
        print(f"{ok:4} {b['_agente']:10} {b.get('severidad','?'):5} {b.get('id','?')[:34]:34} {b.get('sintoma','')[:90]}")
    print(f"\n{sum(b['_coincide'] == 1 for b in todos)}/{len(todos)} aplicables tal cual")


if __name__ == "__main__":
    main(sys.argv[1], "--json" in sys.argv)
