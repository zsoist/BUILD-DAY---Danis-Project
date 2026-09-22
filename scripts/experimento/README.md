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

Ver `docs/METODO.md` para resultados y contexto científico.

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

## Qué flota usar para las voces (medido, 2026-09-22)

El mismo experimento corre con DeepSeek o con GLM. Lo único que cambia es el
modelo: mismo prompt, misma muestra, misma semilla, mismo código de medición.

```bash
ENJAMBRE=deepseek node scripts/experimento/careo_ecp.mjs 160 P5301 /tmp/ds.json
ENJAMBRE=glm      node scripts/experimento/careo_ecp.mjs 160 P5301 /tmp/glm.json
```

Cinco preguntas, 160 voces cada una, careadas contra la ECP 2023:

| pregunta | DeepSeek | GLM 5.3 | desv. DS | desv. GLM |
|---|---|---|---|---|
| P5301 satisfacción con la democracia | **0.084** | 0.154 | 0.77 | 0.59 |
| P2011 importancia de la democracia   | **0.109** | 0.140 | 0.82 | 0.97 |
| P3573 eficacia política              | **0.066** | 0.122 | 0.72 | 0.47 |
| P5302                                | 0.077 | 0.078 | 0.40 | 0.50 |
| P5319 ¿Colombia es democrática?      | 0.095 | 0.095 | 0.33 | 0.33 |

(W1 normalizado, menor es mejor. Razón de desviación: 1.00 sería lo ideal.)

**DeepSeek nunca pierde:** gana claro en tres y empata en dos —0.077 contra
0.078 y 0.095 contra 0.095 son ruido, no ventaja—. En P5301 el fallo de GLM es
cualitativo, no de grado: su W1 (0.154) queda **por encima del baseline de
"todos contestan al azar" (0.108)**, o sea que ahí no sirve. El modo de fallo
es colapso: amontona el 56.6% de las voces en una sola opción, donde los
humanos ponen el 17.0%.

Honestidad sobre la fuerza de la evidencia: son cinco ítems. Con tres
diferencias claras y dos empates, un test de signos da p = 0.125 — dirección
consistente, evidencia modesta. Suficiente para elegir DeepSeek aquí, no para
declarar una ley.

**Esto NO contradice que GLM gane en el enjambre.** Son tareas distintas: para
generar código y entregables GLM devuelve 0% de respuestas vacías contra 17% de
DeepSeek Flash, y no gasta tokens de razonamiento. Simular la dispersión de
opiniones de una población es otro problema, y ahí el que colapsa pierde.

## SSR: no preguntar la escala, reconstruirla (medido, 2026-09-22)

La sub-dispersión era el fallo crónico de todo esto: las voces sintéticas
opinaban más parecido entre sí que los colombianos reales. Probamos el
termómetro 0-100 para quitar el sesgo de formato y **empeoró** — así que el
colapso no estaba en el formato, estaba en tener que escoger casilla.

El método que sí funciona (arXiv:2607.28550, 2026): la persona contesta con sus
palabras, sin ver ninguna escala, y la escala se reconstruye midiendo a qué
punto de anclaje se parece semánticamente lo que dijo. La clave está en el
final: de cada persona se guarda la **distribución completa** de parecidos, no
su anclaje más probable. Quedarse con el máximo sería volver a colapsar.

```bash
ENJAMBRE=deepseek node scripts/experimento/careo_ecp.mjs 160 P5301 /tmp/libre.json libre
uv run --with pyreadstat --with pandas --python 3.12 python scripts/experimento/ssr.py /tmp/libre.json
```

P5301 (satisfacción con la democracia), 160 voces, contra la ECP 2023:

| método | DeepSeek W1 | desv. | GLM W1 | desv. |
|---|---|---|---|---|
| categórico (escoge 1-5) | 0.084 | 0.77 | 0.154 | 0.59 |
| continuo (termómetro 0-100) | 0.154 | 0.65 | 0.174 | 0.65 |
| **SSR (texto libre + anclajes)** | **0.045** | **0.98** | 0.140 | **1.01** |

(W1 menor es mejor. Razón de desviación: 1.00 es lo ideal.)

**La sub-dispersión se acabó.** Pasó de 0.77 y 0.59 a 0.98 y 1.01 — las voces
sintéticas ahora discrepan entre sí tanto como los colombianos reales. Y el
error de DeepSeek casi se parte a la mitad.

Control incluido en el informe: la columna «argmax» aplica el mismo pipeline
pero quedándose con el anclaje más parecido de cada persona. Da W1 0.055 y
desviación 0.84 en DeepSeek, peor en las dos cosas. O sea que guardar la
distribución entera es lo que hace el trabajo, no los embeddings por sí solos.

**Lo que SSR NO arregla: el sesgo.** Con la dispersión ya correcta, a GLM le
queda un problema distinto y más claro de leer: pone el 38.3% de las voces en
"muy insatisfecho" donde los humanos ponen 18.1%, y su media es 2.14 contra
2.70 humana. Sus personas colombianas son sistemáticamente más amargas. Eso es
sesgo del modelo, no del método, y por eso el simulador se queda en DeepSeek.
