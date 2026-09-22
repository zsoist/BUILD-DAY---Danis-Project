# Experimento «¿son personas reales?»

A/B con grupo de control sobre las MISMAS personas y la MISMA pregunta:

- **A** = andamiaje de producción. Los prompts se extraen del `index.html` vivo
  (no hay copia que se desincronice): `persona()` + `sondeoInstr()`.
- **B** = control desnudo: "eres un colombiano de X años, oficio Y, de Z".

La diferencia entre lotes **es** el andamiaje. Semilla fija → reproducible.
Corre sobre DeepSeek; jamás toca la API de Anthropic.

```bash
node scripts/experimento/generar.mjs 28 "tu pregunta" /tmp/exp.json
python3 scripts/experimento/medir.py /tmp/exp.json
```

Las métricas son deterministas y se calculan en Python sobre el texto crudo:
índice de manada (4-gramas propios, excluyendo el vocabulario de la pregunta),
diversidad léxica, arranques distintos, variación de largo, señal de educación
(¿se oye el nivel educativo de la ficha?), obediencia al libreto asignado,
y **V de Cramér identidad→opinión**, la métrica de caricatura de la literatura.

Ningún número lo juzga un modelo de lenguaje.

Ver `METODO.md` en la raíz para resultados y contexto científico.

## Careo contra humanos reales (ECP del DANE)

La prueba dura: la pregunta **literal** de la Encuesta de Cultura Política se le
hace a los residentes sintéticos y se compara contra las respuestas humanas
reales, ponderadas con el factor de expansión oficial.

```bash
node scripts/experimento/careo_ecp.mjs 200 P5301 /tmp/careo.json
uv run --with pyreadstat --with pandas --python 3.12 python scripts/experimento/careo_ecp.py /tmp/careo.json
```

Códigos útiles del módulo de democracia (ver `simcolombia/data/ecp2023_codebook.json`):
`P5301` satisfacción con la democracia · `P2011` importancia de la democracia ·
`P5319` ¿Colombia es democrática? · `P5263S1..S15` confianza en instituciones ·
`P2016S1..S9` percepción de corrupción · `P3573` eficacia política.

Métricas: **W1 normalizado** (distancia sobre la escala ordinal), **razón de
desviación estándar** (detecta sub-dispersión, el fallo clásico) y **tasa de
"no sé"**.

## Baseline humano de caricatura

```bash
uv run --with pyreadstat --with pandas --python 3.12 python scripts/experimento/baseline_ecp.py 2023
```

Calcula cuánto predice la identidad demográfica la opinión en colombianos
reales. Es el patrón contra el que se juzga si el simulador caricaturiza.
