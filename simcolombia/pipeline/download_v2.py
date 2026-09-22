#!/usr/bin/env python3
"""v2 · Descarga de fuentes NUEVAS: electoral (Registraduría vía datos.gov.co),
Cultura Política y lo que los agentes de investigación confirmen.

Estrategia Socrata: los datasets a nivel MESA tienen millones de filas — se
bajan AGREGADOS server-side con SoQL (group by), no crudos. Lo crudo mesa-level
solo si un análisis lo pide (y por departamento, paginado).

Salida: simcolombia/data/raw_v2/ (gitignored, como raw/).
"""
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
RAW = BASE / "data" / "raw_v2"
RAW.mkdir(parents=True, exist_ok=True)

SOCRATA = "https://www.datos.gov.co/resource"


def soql(res_id, query, out_name):
    """Baja un agregado SoQL completo (pagina de a 50k)."""
    filas, offset = [], 0
    while True:
        q = f"{query}&$limit=50000&$offset={offset}"
        url = f"{SOCRATA}/{res_id}.json?{q}"
        with urllib.request.urlopen(url, timeout=120) as r:
            lote = json.load(r)
        filas += lote
        if len(lote) < 50000:
            break
        offset += 50000
    out = RAW / out_name
    json.dump(filas, out.open("w"), ensure_ascii=False)
    print(f"✅ {out_name}: {len(filas):,} filas")
    return filas


# ── ELECTORAL (verificado a mano 2026-09-21) ────────────────────────────────
ELECTORAL = {
    # Senado 2018, nivel mesa → agregamos por dpto×candidato (partido viene en candidato)
    "senado2018_dpto": ("75f2-fe2s",
        urllib.parse.quote("$select=ndepto,candidato,sum(votos) as votos"
                           "&$group=ndepto,candidato", safe="$=&,()"),
        "senado2018_dpto.json"),
    # Cámara 2018 nivel mesa → dpto×candidato
    "camara2018_dpto": ("vkjr-c6fe",
        urllib.parse.quote("$select=ndepto,candidato,sum(votos) as votos"
                           "&$group=ndepto,candidato", safe="$=&,()"),
        "camara2018_dpto.json"),
}


def electoral():
    for _, (rid, q, out) in ELECTORAL.items():
        try:
            soql(rid, q, out)
        except Exception as e:
            print(f"⚠️ {out}: {e}")





# ── DESCARGA MAESTRA (URLs verificadas por agentes 2026-09-21) ──────────────
import subprocess, time

def dl_dane(catalogo, file_id, out):
    """Receta anti-WAF de ANDA: visitar get-microdata con cookies, luego bajar."""
    if (RAW/out).exists() and (RAW/out).stat().st_size > 1000:
        print(f"↷ {out} ya existe"); return
    jar = "/tmp/anda_cookies.txt"
    subprocess.run(["curl","-s","-c",jar,"-b",jar,"-o","/dev/null",
        f"https://microdatos.dane.gov.co/index.php/catalog/{catalogo}/get-microdata"])
    r = subprocess.run(["curl","-sL","-b",jar,"--retry","5","--retry-delay","30",
        "--retry-all-errors","-o",str(RAW/out),
        f"https://microdatos.dane.gov.co/index.php/catalog/{catalogo}/download/{file_id}"])
    tam = (RAW/out).stat().st_size if (RAW/out).exists() else 0
    print(("✅" if tam>10000 else "⚠️"), out, f"{tam:,}B"); time.sleep(15)

def dl_url(url, out):
    if (RAW/out).exists() and (RAW/out).stat().st_size > 1000:
        print(f"↷ {out} ya existe"); return
    subprocess.run(["curl","-sL","--retry","4","--retry-delay","20","--retry-all-errors",
                    "-o",str(RAW/out),url])
    tam = (RAW/out).stat().st_size if (RAW/out).exists() else 0
    print(("✅" if tam>1000 else "⚠️"), out, f"{tam:,}B"); time.sleep(5)

def maestra():
    OBS = "https://observatorio.registraduria.gov.co"
    # electoral nivel mesa (Registraduría)
    dl_url(f"{OBS}/anexos/MMV_NACIONAL_PRESIDENTE_2022_1v.zip","pres2022_1v.zip")
    dl_url(f"{OBS}/anexos/MMV_NACIONAL_PRESIDENTE_2022_2v.zip","pres2022_2v.zip")
    dl_url(f"{OBS}/anexos/MMV_NACIONAL_PRESIDENTE_2018_2v.zip","pres2018_2v.zip")
    dl_url(f"{OBS}/anexos/MMV_NACIONAL_PRESIDENTE_2018_1v.zip","pres2018_1v.zip")
    dl_url(f"{OBS}/anexos/MMV_Presidente1V_2026.zip","pres2026_1v.zip")
    dl_url(f"{OBS}/anexos/MMV_Presidente2V_2026.zip","pres2026_2v.zip")
    # plebiscito + censo electoral + puestos georref
    dl_url("https://data.humdata.org/dataset/a4bddf8b-6c45-4592-97d4-a2af975bf88f/resource/6337548b-87b3-4e93-b1f5-81483aeb3a9b/download/resultados_plebiscito.xls","plebiscito2016_mpio.xls")
    dl_url("https://s3.amazonaws.com/uploads.dskt.ch/moe/datos-electorales/censo_electoral.csv","censo_electoral_puesto.csv")
    dl_url("https://www.datos.gov.co/resource/mv2e-prx5.csv?$limit=20000","divipole2023_georef.csv")
    # pobreza (DANE xlsx, serie histórica en hojas)
    for f in ("anex-PMDepartamental-2025.xlsx","anex-PMultidimensional-Departamental-2025.xlsx",
              "anex-PM-TotalNacional-2025.xlsx","anex-PMClasesSociales-2025.xlsx"):
        dl_url(f"https://www.dane.gov.co/files/operaciones/PM/{f}", f)
    # ECP — la joya de calibración: 2023 completo + Democracia/Elecciones históricos
    for fid,out in [(23355,"ecp2023_caracteristicas.zip"),(23358,"ecp2023_democracia.zip"),
                    (23359,"ecp2023_elecciones.zip"),(23360,"ecp2023_participacion.zip"),
                    (23357,"ecp2023_capital_social.zip")]:
        dl_dane(822,fid,out)
    for cat,fid,out in [(730,21030,"ecp2021_democracia.zip"),(730,21027,"ecp2021_elecciones.zip"),
                        (644,21024,"ecp2019_democracia.zip"),(515,8883,"ecp2017_democracia.zip"),
                        (406,6593,"ecp2015_democracia.zip")]:
        dl_dane(cat,fid,out)
    # GEIH: julio 2026 (lo más fresco) + 2025 completo + puntas de 2024
    dl_dane(900,24791,"geih_2026_07.zip")
    for fid,mes in [(24263,"01"),(24264,"02"),(24267,"03"),(24269,"04"),(24268,"05"),(24266,"06"),
                    (24265,"07"),(24307,"08"),(24324,"09"),(24382,"10"),(24406,"11"),(24463,"12")]:
        dl_dane(853,fid,f"geih_2025_{mes}.zip")
    dl_dane(819,23313,"geih_2024_01.zip"); dl_dane(819,23794,"geih_2024_12.zip")
    # territoriales país completo (grandes — al final)
    dl_url(f"{OBS}/comprimidos/MMV_TERRITORIALES2023_COLOMBIA.zip","territoriales2023.zip")
    dl_url(f"{OBS}/comprimidosTwo/MMV_TERRITORIALES2019_COLOMBIA.zip","territoriales2019.zip")
    print("\n🏁 descarga maestra terminada"); subprocess.run(["du","-sh",str(RAW)])


if __name__ == "__main__":
    cual = sys.argv[1] if len(sys.argv) > 1 else "electoral"
    if cual == "electoral":
        electoral()
    elif cual == "maestra":
        maestra()
