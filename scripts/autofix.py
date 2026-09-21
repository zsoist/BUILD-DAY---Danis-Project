#!/usr/bin/env python3
"""Ciclo autónomo de fixes: hallazgos → agentes escriben PARCHES → se aplican
con compuertas (match exacto + chequeo de sintaxis). Claude aprueba el lote.

Uso:
  python scripts/autofix.py plan <run_dir_hallazgos>   # emite orchestrator/plans/fixes.json
  python scripts/autofix.py apply <run_dir_parches>    # aplica con compuertas
"""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHIVO_POR_TAREA = {  # de qué archivo habla cada tarea de hallazgos
    "r2_api": "api/opina.js",
    "r5_showtime": "simcolombia/fable/showtime.py",
    "r5_effswarm": "orchestrator/swarm.py",
    "r5_effsim": "dashboard/sim/index.html",
    "r5_visor2": "dashboard/index.html",
    "r5_gen2": "simcolombia/pipeline/generate_population.py",
    # nota: los parches se validan por match-único contra el archivo destino,
    # así que un mapeo errado se rechaza solo — pero mejor acertar:
}
SALTAR = {"r5_evento"}  # hallazgos estructurales (guion) — los arregla Claude a mano
def archivo_de(stem):
    if stem in ARCHIVO_POR_TAREA:
        return ARCHIVO_POR_TAREA[stem]
    return "api/opina.js" if "api" in stem else DEFAULT_FILE
DEFAULT_FILE = "dashboard/sim/index.html"


def clean(t):
    return re.sub(r"^```(?:json)?|```$", "", t.strip(), flags=re.M).strip()


def plan(run_dir: Path):
    tasks = []
    for f in sorted(run_dir.glob("artifacts/*.json")):
        try:
            d = json.loads(clean(f.read_text()))
        except Exception:
            continue
        if f.stem in SALTAR:
            continue
        archivo = archivo_de(f.stem)
        code = (ROOT / archivo).read_text()
        altas = [h for h in d.get("hallazgos", []) if h.get("gravedad") == "alta"]
        for i, h in enumerate(altas[:3]):
            tasks.append({
                "id": f"fx_{f.stem}_{i}", "thinking": "medium",
                "filename": f"fx_{f.stem}_{i}.json",
                "prompt": (
                    'Devuelve SOLO JSON crudo: {"parches":[{"buscar":"...","reemplazar":"..."}]} '
                    "— máximo 3 parches quirúrgicos que arreglen SOLO este hallazgo. "
                    "REGLAS DURAS: 'buscar' debe ser una subcadena EXACTA y ÚNICA del código "
                    "(cópiala literal, con sus espacios y saltos); 'reemplazar' la versión "
                    "corregida completa de ese fragmento; NO reformatees nada más; NO toques "
                    "otras funciones; conserva el estilo. Si el hallazgo no es arreglable con "
                    'parches seguros, devuelve {"parches":[]}.\n\n'
                    f"HALLAZGO en {archivo}: [{h.get('donde','?')}] {h.get('problema','')} "
                    f"FIX SUGERIDO: {h.get('fix','')}\n\nCÓDIGO COMPLETO:\n```\n{code[:60000]}\n```"
                ),
            })
    out = ROOT / "orchestrator" / "plans" / "fixes.json"
    json.dump({"task": "Parches quirúrgicos para los hallazgos de gravedad alta.",
               "tasks": tasks}, out.open("w"), ensure_ascii=False)
    print(f"{len(tasks)} tareas de fix → {out}")


def check(path: Path) -> bool:
    if path.suffix == ".js":
        return subprocess.run(["node", "--check", str(path)],
                              capture_output=True).returncode == 0
    if path.suffix == ".py":
        return subprocess.run([sys.executable, "-m", "py_compile", str(path)],
                              capture_output=True).returncode == 0
    if path.suffix == ".html":
        js = re.search(r"<script>(.*)</script>", path.read_text(), re.S)
        p = Path("/tmp/_chk.js"); p.write_text(js.group(1) if js else "")
        return subprocess.run(["node", "--check", str(p)],
                              capture_output=True).returncode == 0
    return True


def apply(run_dir: Path):
    aplicados, rechazados = [], []
    for f in sorted(run_dir.glob("artifacts/fx_*.json")):
        try:
            parches = json.loads(clean(f.read_text())).get("parches", [])
        except Exception:
            rechazados.append((f.stem, "json inválido")); continue
        stem = f.stem.replace("fx_", "").rsplit("_", 1)[0]
        archivo = ROOT / archivo_de(stem)
        original = archivo.read_text()
        texto = original
        ok = True
        for p in parches:
            b, r = p.get("buscar", ""), p.get("reemplazar", "")
            if not b or texto.count(b) != 1:      # compuerta 1: match exacto y único
                ok = False; break
            texto = texto.replace(b, r)
        if not ok or texto == original:
            rechazados.append((f.stem, "sin match único o vacío")); continue
        archivo.write_text(texto)
        if not check(archivo):                     # compuerta 2: sintaxis
            archivo.write_text(original)
            rechazados.append((f.stem, "rompía sintaxis — revertido")); continue
        aplicados.append(f.stem)
    print(f"✅ aplicados: {aplicados}")
    print(f"⛔ rechazados: {rechazados or 'ninguno'}")


if __name__ == "__main__":
    cmd, run = sys.argv[1], Path(sys.argv[2])
    run = run if run.is_absolute() else ROOT / run
    plan(run) if cmd == "plan" else apply(run)
