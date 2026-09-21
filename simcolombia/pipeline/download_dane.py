#!/usr/bin/env python3
"""Baja las fuentes reales de Sim Colombia → data/raw/.

Fuentes (verificadas 2026-09-21):
  - PIB departamental (datos.gov.co kgyi-qc7j) — economía por dpto
  - Cobertura salud por municipio (23gb-dhmd) — régimen contributivo/subsidiado
  - Proyecciones DANE dpto×sexo×edad (URL en DANE_PROYECCIONES, la llena el research)
Uso: uv run --project orchestrator python simcolombia/pipeline/download_dane.py
"""
import json
import urllib.request
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

SOCRATA = {
    "pib_departamental.json":
        "https://www.datos.gov.co/resource/kgyi-qc7j.json?$limit=50000",
    "salud_municipios.json":
        "https://www.datos.gov.co/resource/23gb-dhmd.json?$limit=50000",
}

# La llena el agente de research (archivo canónico DANE dpto x sexo x edad)
DANE_PROYECCIONES = ""


def fetch(url: str, dest: Path):
    print(f"↓ {dest.name} ← {url[:80]}")
    req = urllib.request.Request(url, headers={"User-Agent": "simcolombia/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())
    print(f"  {dest.stat().st_size/1e6:.1f} MB")


if __name__ == "__main__":
    for name, url in SOCRATA.items():
        fetch(url, RAW / name)
    if DANE_PROYECCIONES:
        ext = DANE_PROYECCIONES.rsplit(".", 1)[-1].split("?")[0]
        fetch(DANE_PROYECCIONES, RAW / f"proyecciones_dane.{ext}")
    else:
        print("⚠️  DANE_PROYECCIONES vacío — pendiente del research")
