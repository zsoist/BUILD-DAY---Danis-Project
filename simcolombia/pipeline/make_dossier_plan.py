#!/usr/bin/env python3
"""Genera el plan de batalla del enjambre: 33 dossiers departamentales.

Cada prompt lleva LOS NÚMEROS REALES del dpto (PIB sectorial, salud) — el agente
pone contexto y carne, nunca cifras. Jev vigila verosimilitud y estereotipos.
Salida: orchestrator/plans/dossiers.json
"""
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
M = json.loads((BASE / "data" / "marginals.json").read_text())["departamentos"]
tasks = []
for cod, d in sorted(M.items()):
    sect = ", ".join(f"{k} {v}%" for k, v in list(d.get("pib_sectores_pct", {}).items())[:4])
    sal = d.get("salud_pct", {})
    tasks.append({
        "id": f"d{cod}", "thinking": "none",
        "filename": f"dossier_{cod}.json",
        "prompt": (
            "Devuelve SOLO JSON crudo (sin ```): "
            '{"cod":"%s","nombre":"%s","apodo_gentilicio":"...","como_hablan":"...",'
            '"vida_cotidiana":"...","economia_vivida":"...","orgullos":["...","..."],'
            '"dolores":["...","..."],"ocupaciones_tipicas":["..x6.."],'
            '"nombres_frecuentes":{"mujer":["..x8.."],"hombre":["..x8.."]},'
            '"apellidos":["..x10.."]}\n'
            "Departamento: %s (Colombia). DATOS REALES que debes respetar (no los "
            "repitas como cifras, tradúcelos a vida): estructura económica %s; "
            "salud: %s%% contributivo / %s%% subsidiado. "
            "Campos de texto: máximo 220 caracteres cada uno, español colombiano "
            "neutro, concreto y respetuoso — cero caricatura, cero folclorismo "
            "barato; gente real, matizada. ocupaciones_tipicas coherentes con la "
            "estructura económica dada."
        ) % (cod, d["nombre"], d["nombre"], sect or "n/d",
             sal.get("contributivo", "?"), sal.get("subsidiado", "?")),
    })
out = Path(__file__).resolve().parents[2] / "orchestrator" / "plans" / "dossiers.json"
json.dump({"task": "33 dossiers departamentales de Sim Colombia con datos DANE "
                   "reales: contexto vivido por departamento para dar carne a los "
                   "residentes sintéticos.", "tasks": tasks},
          out.open("w"), ensure_ascii=False, indent=1)
print(f"{len(tasks)} tareas → {out}")
