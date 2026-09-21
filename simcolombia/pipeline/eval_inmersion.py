#!/usr/bin/env python3
"""QA de inmersión: corre N preguntas por el motor real de personas y guarda
los transcripts para que un jurado de agentes los evalúe.

Replica el persona() del sim (mismo hash, mismos ejes) contra deepseek-flash.
Salida: simcolombia/data/eval/transcripts.json
"""
import asyncio
import json
import os
import random
import re
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI

BASE = Path(__file__).resolve().parent.parent
load_dotenv(BASE.parent / ".env")
ds = AsyncOpenAI(api_key=os.environ["DEEPSEEK_API_KEY"],
                 base_url="https://api.deepseek.com")

RES = json.loads((BASE.parent / "dashboard/sim/residents.json").read_text())
DOS = json.loads((BASE.parent / "dashboard/sim/dossiers.json").read_text())

TEMPERAMENTOS = [
 "seco/a y de pocas palabras: respondes en UNA frase corta y ya",
 "parlanchín/a: metes una anécdota tuya concreta en 2-3 frases",
 "sarcástico/a suave: rematas con ironía fina",
 "conciliador/a: buscas el punto medio y bajas los ánimos",
 "quejumbroso/a: todo te recuerda una queja concreta de tu vida",
 "entusiasta: le ves lo bueno y lo dices con energía",
 "escéptico/a: pides pruebas, desconfías de promesas",
 "pragmático/a: hablas de plata y números concretos",
 "chistoso/a: metes una broma corta sin payasada",
 "tímido/a: opinas bajito, con 'no sé, pero…', y aún así opinas",
 "indignado/a: esto te toca personal y se nota",
 "profesoral: explicas con calma, un dato y listo"]
LEAN = ["estás A FAVOR por algo concreto que viviste, y lo defiendes"]*2 + \
       ["estás EN CONTRA por algo concreto que viviste, y lo defiendes"]*2 + \
       ["llegas dividido/a de verdad: tu vida te jala para los dos lados"]
FRANQ = ["SIN FILTRO: dices lo que piensas aunque suene políticamente incorrecto (sin insultos)"]*2 + \
        ["FRANCO/A con humor: sueltas la opinión espinosa envuelta en chiste",
         "DIPLOMÁTICO/A: mides las palabras, pero tu postura se nota",
         "DE PULLA: te encanta picar al de la otra región/orilla, con cariño pero picas"]
ARRANQUES = ["arrancas con tu postura seca, sin preámbulo","arrancas con una pregunta retórica tuya",
 "arrancas por la anécdota","arrancas negando lo que 'todo el mundo dice'","arrancas con un dato que te sabes",
 "arrancas con humor o comparación tuya","arrancas dirigiéndote a quien pregunta","arrancas por lo que viviste esta semana"]
DIAL = {
 tuple("08 13 20 23 44 47 70".split()): "CARIBE: te comes las eses ('vamo a vé'), 'ajá','ombe', ritmo rápido",
 tuple("05 17 63 66".split()): "PAISA: voseas ('vos sabés'), 'pues','¿cierto?','mijo'",
 tuple("54 68".split()): "SANTANDEREANO: seco, directo, ustedeo, 'mano'",
 tuple("11 15 25".split()): "CUNDIBOYACENSE: usted/sumercé, 'o sea','¿sí o qué?'",
 tuple("76 19".split()): "VALLUNO: 'mirá vé','oís', cadencia cantada",
 tuple(["52"]): "PASTUSO: pausado, amable", tuple("50 81 85 95 99".split()): "LLANERO: recio, 'camarita'",
 tuple("41 73".split()): "OPITA: tranquilo, 'ala'", tuple(["27"]): "PACÍFICO: expresivo, 've hombe'",
 tuple("18 86 91 94 97".split()): "AMAZÓNICO: pausado y concreto", tuple(["88"]): "RAIZAL: mezcla creole, 'man'"}


def h32(s):
    h = 0
    for c in s:
        h = (h * 37 + ord(c)) & 0xFFFFFFFF
    return h


def persona(r, opc=None):
    d = DOS.get(r["dpto"], {})
    h = h32(r["id"])
    temp, lean, franq = (TEMPERAMENTOS[h % 12], LEAN[(h >> 4) % 5], FRANQ[(h >> 8) % 5])
    dial = next((v for k, v in DIAL.items() if r["dpto"] in k), "")
    mule = " · ".join(d.get("muletillas", [])[:6])
    riv = " · ".join(d.get("rivalidades", [])[:2])
    eleccion = (f"LA PREGUNTA ES UNA ELECCIÓN: [POSTURA: a_favor] = eliges «{opc[0]}», "
                f"[en_contra] = «{opc[1]}», [depende] solo si no vas con ninguno.\n") if opc else ""
    return f"""Eres {r['nombre']}, {r['edad']} años, {r['sexo']}, {r['ocupacion']}, estudios: {r.get('educacion','')}, régimen {r['regimen_salud']}, de {r['dpto_nombre']}, Colombia.
Tu tierra: {d.get('vida_cotidiana','')} {d.get('economia_vivida','')}
QUIÉN ERES AL HABLAR: eres {temp}. Sobre el tema de hoy, {lean}. {eleccion}Tu postura asignada ES la tuya y la defiendes. Franqueza: eres {franq}.
LA VERDAD INCÓMODA: la gente real tiene prejuicios, manías y rivalidades — si tu personaje las tendría, DILAS (sin insultos). Tu edad, educación y territorio MOLDEAN tu opinión.
Acento SUTIL ({dial.split(':')[0] if dial else 'tu región'}): un rasgo de vez en cuando, jamás el cliché que ya dijo otro. Expresiones (máx una si cuadra): {mule or '—'}.
{'Pullas de tu tierra (una con picardía si cuadra): '+riv if riv else ''}
TU ARRANQUE (obligatorio): {ARRANQUES[(h>>11)%8]}.
REGLAS DURAS: primera persona, concreta TU vida; PROHIBIDO arrancar con "Vea pues","Mire","Le digo una cosa","Uy"; SOLO expresiones de TU región o ninguna; no afirmes datos que no te constan (fútbol: Nacional/DIM=Medellín, Millos/Santa Fe=Bogotá, América/Cali=Valle, Junior=Barranquilla); OBEDECE tu inclinación asignada y que la etiqueta coincida con el texto; sin groserías pesadas; prohibido sonar a IA.
Responde la encuesta en 1-2 frases con POSTURA CLARA y cierra con [POSTURA: a_favor|en_contra|depende]."""


PREGUNTAS = [
 "¿millos o nacional?", "¿Vale la pena irse del país?",
 "¿arepa con queso o arepa sola?", "¿Qué opinan de los rolos?",
 "¿El salario mínimo alcanza para vivir?", "¿Uber o taxi?",
 "¿Deberían legalizar la marihuana?", "¿El café colombiano es el mejor del mundo o puro cuento?",
 "¿Confían en la policía?", "¿vallenato o reggaetón?",
 "¿Los jóvenes de hoy son más vagos que antes?", "¿Pagar arriendo es botar la plata?",
]
AOB = re.compile(r"^¿?\s*(.{2,28}?)\s+o\s+(.{2,28}?)\s*\??$", re.I)


async def voz(r, q, opc):
    resp = await ds.chat.completions.create(
        model="deepseek-flash", max_tokens=150, temperature=0.95,
        extra_body={"thinking": {"type": "disabled"}},
        messages=[{"role": "system", "content": persona(r, opc)},
                  {"role": "user", "content": q}])
    txt = resp.choices[0].message.content or ""
    m = re.search(r"\[POSTURA:?\s*(a_favor|en_contra|depende)", txt, re.I)
    return {"quien": f"{r['nombre']}, {r['edad']}, {r['ocupacion']}, {r['dpto_nombre']}",
            "postura": m.group(1).lower() if m else None,
            "texto": re.sub(r"\[POSTURA[^\]]*\]?", "", txt).strip()}


async def main():
    rng = random.Random(6)
    out = []
    sem = asyncio.Semaphore(12)
    async def una(q):
        m = AOB.match(q)
        opc = (m.group(1), m.group(2)) if m else None
        pool = [r for r in RES if r["edad"] >= 16]
        sample = rng.sample(pool, 4)
        async with sem:
            voces = await asyncio.gather(*(voz(r, q, opc) for r in sample))
        out.append({"pregunta": q, "opciones": opc, "voces": voces})
        print(f"✓ {q}")
    await asyncio.gather(*(una(q) for q in PREGUNTAS))
    d = BASE / "data" / "eval"; d.mkdir(exist_ok=True)
    (d / "transcripts.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"\n{len(out)} preguntas × 4 voces → {d/'transcripts.json'}")

asyncio.run(main())
