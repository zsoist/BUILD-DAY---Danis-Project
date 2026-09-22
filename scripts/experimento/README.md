# Experimento: cómo se mide si el simulador sirve

Población: 8.000 personas sintéticas en 33 departamentos (85 a 875 según población). Cada una es una persona real encuestada por el DANE en la GEIH (13 meses de microdatos), repesada con proyecciones DANE 2026. La ECP 2023 (46.392 adultos reales) no es la fuente: es contra lo que se comparan las respuestas.

## Flujo de 3 pasos

```bash
# 1. Generar voces
ENJAMBRE=deepseek node scripts/experimento/careo_ecp.mjs 160 P5301 /tmp/careo.json
# 2. Medir contra humanos reales
uv run python scripts/experimento/careo_ecp.py /tmp/careo.json
# 3. Baseline: qué predice la demografía en colombianos reales
uv run python scripts/experimento/baseline_ecp.py 2023
```

El entorno Python está en la raíz del repo (Python 3.12). El simulador vive en `web/`. Enjambre de agentes: github.com/zsoist/SWARMS.

## Scripts

| script | qué hace |
|---|---|
| `careo_ecp.mjs` | N voces para una pregunta de la ECP. Modos `categorico\|continuo\|libre`. `ENJAMBRE=deepseek\|glm`, `TEMP_VOZ` |
| `careo_ecp.py` | Mide contra la ECP ponderada: W1 normalizado, razón de desviación, baselines de azar |
| `ssr.py` | SSR sobre salida en modo libre. Embeddings `openai/text-embedding-3-small` vía OpenRouter, T=0.25 |
| `generar.mjs` + `medir.py` | A/B «¿son personas reales?»: andamiaje de producción contra control desnudo. Medidor determinista |
| `baseline_ecp.py` | Cuánto predice la demografía la opinión en colombianos reales: patrón contra el que se juzga la caricatura |
| `abstencion_gen.mjs`, `abstencion.py`, `abstencion_valida.py` | «No sé» calibrado: reproduce el gradiente por educación de cada persona, falla por ítem |
| `irtree.py`, `careo_irtree.py`, `irtree_calibracion.json`, `careo_holdout_*.json` | IRTree, RECHAZADO. Se conserva como resultado negativo |

## Resultados vigentes (2026-09-22)

### Qué flota usar para las voces

Cinco preguntas, 160 voces cada una, contra la ECP 2023:

| pregunta | DeepSeek | GLM 5.3 | desv. DS | desv. GLM |
|---|---|---|---|---|
| P5301 satisfacción con la democracia | **0.084** | 0.154 | 0.77 | 0.59 |
| P2011 importancia de la democracia   | **0.109** | 0.140 | 0.82 | 0.97 |
| P3573 eficacia política              | **0.066** | 0.122 | 0.72 | 0.47 |
| P5302                                | 0.077 | 0.078 | 0.40 | 0.50 |
| P5319 ¿Colombia es democrática?      | 0.095 | 0.095 | 0.33 | 0.33 |

W1 normalizado, menor es mejor; razón de desviación 1.00 ideal. DeepSeek gana 3, empata 2 (p = 0.125, test de signos: evidencia modesta, suficiente para elegir). GLM en P5301 colapsa: 56.6% en una opción donde los humanos ponen 17.0%, W1 encima del azar (0.108). No contradice que GLM gane en el enjambre para código y entregables; simular dispersión de opinión es otro problema.

### Qué método usar

| método | DeepSeek W1 | desv. | GLM W1 | desv. |
|---|---|---|---|---|
| categórico (escoge 1-5) | 0.084 | 0.77 | 0.154 | 0.59 |
| continuo (termómetro 0-100) | 0.154 | 0.65 | 0.174 | 0.65 |
| **SSR (texto libre + anclajes)** | **0.045** | **0.98** | 0.140 | **1.01** |

SSR: la persona contesta con sus palabras, la escala se reconstruye por parecido semántico con anclajes, guardando la distribución completa de parecidos (el control «argmax» da W1 0.055 y desv. 0.84: guardar la distribución es lo que funciona). La sub-dispersión quedó resuelta.

Sesgo que SSR no arregla: GLM pone 38% en «muy insatisfecho» donde los humanos ponen 18%. El simulador se queda en DeepSeek.

## Lo descartado y por qué

- **Termómetro 0-100**: empeoró (W1 0.084 → 0.154). El colapso estaba en escoger casilla, no en el formato.
- **IRTree**: calibración W1 0.019, holdout 0.272 — peor que el azar. Conservado como resultado negativo.
- **«No sé» calibrado**: reproduce el gradiente por educación de cada persona, falla por ítem.
- **Fable/Anthropic**: apagado para siempre.

Este repo no es una encuesta, no tiene margen de error, no se usa para campañas ni segmentación de votantes. Contexto y resultados: `docs/METODO.md`.
## Posturas sí/no (lo que hace el sitio)

| Variable / script | Qué |
|---|---|
| `ENJAMBRE=sitio` | misma ruta que producción: `deepseek/deepseek-v4.1-flash` por OpenRouter |
| `LIBRETO=0` | sin la postura sorteada 40/40/20 (por defecto 1, como el sitio) |
| `postura.py` | % de "sí" de las voces contra la ECP (P5261S1-S8), categórico y SSR |
| modo `sitio` | el prompt real del sondeo: texto + etiqueta de la misma voz |
| `mezcla.py` | mezcla etiqueta+SSR con la regla de despliegue fijada |
| `anclas.test.mjs` | falla si anclas, T o α del sitio se apartan de lo medido |

Resultado: la mezcla se desplegó en el sondeo; `docs/METODO.md`, sección "Mezcla".
