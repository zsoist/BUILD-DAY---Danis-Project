# ColombIA ¡Que Piensa! — Método, alcance y límites

> **Qué es**: un simulador de población colombiana. 8.000 residentes en 33 departamentos (de 85 a 875 según población). Cada uno toma sus variables socioeconómicas de una **persona real encuestada por el DANE** (GEIH 2025 – jul 2026), repesada con proyecciones DANE 2026; nombre y personalidad son generados. Las opiniones las produce un modelo de lenguaje.
>
> **Qué NO es**: una encuesta. No mide opinión pública colombiana. No tiene margen de error. Ninguno de estos residentes existe.

## 1. De dónde sale cada cosa

| Capa | Fuente | Naturaleza |
|---|---|---|
| Edad, sexo, educación, oficio (CIUO-08), ingreso, régimen de salud, urbano/rural | Microdatos GEIH del DANE, 13 meses (2025 – jul 2026) | Real, muestreada conjuntamente |
| Peso de expansión | `FEX_C18` de la GEIH | Real |
| Población, pirámide de edad, % urbano por departamento | Proyecciones DANE 2026 | Real |
| Pobreza monetaria, Gini, PIB sectorial | Anexos oficiales DANE 2025 | Real |
| Inclinación política territorial | Senado 2018 a nivel de mesa (datos.gov.co) | Real, agregada por departamento |
| Nombre, apellido, retrato | Generados por frecuencias regionales | Sintético |
| Temperamento, franqueza, arranque, marco social, fundamento | Deterministas por hash del id | Sintético |
| Lo que dice | deepseek/deepseek-v4.1-flash vía OpenRouter, con el prompt del residente | Generado |

El muestreo es **conjunto**: se toma una persona GEIH completa, no "una edad" y "un oficio" por separado. Eso preserva las combinaciones que existen de verdad y evita las quimeras de los métodos marginales.

**Sesgo de cobertura**: la GEIH solo encuesta cabeceras en Amazonas, Guainía, Vaupés y Vichada. Se imputa la cuota rural del marginal DANE de forma determinista (`simcolombia/pipeline/generate_population_v2.py`).

**Reproducibilidad**: entorno Python 3.12 en la raíz del repo; todo se corre con `uv run python <script>`.

## 2. Validación (9 chequeos deterministas)

`simcolombia/pipeline/validar_v2.py` se corre a mano (el despliegue no tiene paso de build). **Ninguna cifra la juzga un modelo de lenguaje.**

| # | Chequeo | Umbral | Último resultado |
|---|---|---|---|
| 1 | MAE pirámide edad×sexo por dpto | ≤ 0.050 | 0.0100 |
| 2 | Coherencia conjunta (reglas duras) | == 0 | 0 |
| 3 | Masa poblacional (suma de pesos) | ±2% | +0.90% |
| 4 | Compromiso político vs objetivo | ±5 pp | 3.7 pp |
| 5 | Inclinación vs perfiles 2018 | ±5 pp | 4.2 pp |
| 6 | Salud contributiva por dpto | ±6 pp | 0.9 pp |
| 7 | Urbano vs marginal por dpto | ±6 pp | 5.1 pp |
| 8 | Ingreso plausible (mediana y P99) | 0.8–3M / <60M | 1.40M |
| 9 | Compromiso 60+ > 18-29 (direccional) | positivo | +22.6 pp |

## 3. Las voces

Modelo principal **deepseek/deepseek-v4.1-flash** (OpenRouter); respaldo **z-ai/glm-5.3-flash**. En el careo de cinco preguntas contra la ECP, DeepSeek gana 3 y empata 2.

### A/B: andamiaje vs prompt desnudo

Los mismos residentes contestan la misma pregunta con andamiaje (A) y con prompt desnudo (B); diferencias medidas en Python sobre el texto crudo (`scripts/experimento/`).

| Métrica | A (andamiaje) | B (control) |
|---|---|---|
| Diversidad léxica | **26.1%** | 24.5% |
| Arranques distintos | **85.7%** | 67.9% |
| Variación de largo (CV) | **0.333** | 0.179 |
| Señal de educación (r) | **+0.32** | +0.07 |
| Índice de manada (4-gramas propios) | **0.49** | 0.61 |

### Caricatura, contra colombianos de verdad

La **ECP 2023 del DANE (n=46.392 adultos)** no es la fuente de las personas: es contra lo que se comparan las respuestas. En humanos reales (V de Cramér, mediana, 68 preguntas): edad 0.048 · educación 0.071 · sexo 0.021 — la demografía casi no predice la opinión.

Nuestras voces (n=160, permutación de 1.500 barajadas):

| Atributo | A · andamiaje | B · control desnudo |
|---|---|---|
| edad → postura | 0.104 (p=0.86, azar) | 0.256 (p=0.002, **señal real**) |
| educación → postura | 0.093 (p=0.71, azar) | 0.133 (p=0.26, azar) |
| sexo → postura | 0.016 (p=1.00, azar) | 0.224 (p=0.023, **señal real**) |

El prompt desnudo caricaturiza: inventa relaciones edad/sexo→opinión que en Colombia no existen. Con andamiaje, ninguna asociación se distingue del azar.

> Corrección honesta: una versión anterior reportaba "0.23 vs 0.312" con n=28; la V de azar de ese n era 0.275 (ruido). Se repitió con n=160 y control de azar.

## 4. El careo: la pregunta del DANE, a sintéticos y a humanos

Pregunta **literal** de la ECP 2023 sobre satisfacción con la democracia (1-5) a 200 residentes, contra humanos ponderados con el factor de expansión oficial (`scripts/experimento/careo_ecp.mjs` + `.py`).

| Opción | Colombianos reales | Sintéticos (antes) | Sintéticos (después) |
|---|---|---|---|
| 1 muy insatisfecho | 18.1% | 42.7% | 3.0% |
| 2 insatisfecho | 17.0% | 51.3% | 60.3% |
| **3 ni una ni otra** | **46.0%** | **6.0%** | **36.7%** |
| 4 satisfecho | 14.0% | 0.0% | 0.0% |
| 5 muy satisfecho | 4.8% | 0.0% | 0.0% |
| media de la escala | 2.70 | 1.63 | 2.34 |
| **W1 normalizado** | — | **0.268** | **0.168** |

Diagnóstico: los sintéticos estaban más furiosos que los humanos; el punto medio casi no existía. Corregido con regla explícita: *el punto medio de una escala es legítimo y mayoritario*.

### Sub-dispersión: SSR

El fallo central de Bisbee et al.: las voces opinan más parecido entre sí que la gente real. Lo vigente es **SSR** (respuesta en texto libre con anclajes semánticos): razón de desviación **0.77 → 0.98** (1.00 ideal), sin mostrarle jamás al modelo la distribución objetivo. Antecedente: el estilo de respuesta determinista por hash, que la subía solo a 0.79. El termómetro 0-100 como reemplazo de la escala **empeoró** el ajuste (W1 0.084 → 0.154) y se descartó.

Sesgo que SSR no arregla: GLM pone 38% en "muy insatisfecho" donde los humanos responden 18%.

### ¿Le gana a no hacer nada?

| Pregunta | Simulador | Azar | Lo más común | ¿Gana? |
|---|---|---|---|---|
| Satisfacción con la democracia (afinada) | **0.099** | 0.108 | 0.192 | sí, por poco |
| Eficacia política (sin tocar) | **0.056** | 0.238 | 0.166 | sí, con holgura |

Con tres preguntas de la ECP (dos negativas para el país, una positiva):

| Pregunta | W1 | azar | moda |
|---|---|---|---|
| Eficacia política (negativa) | **0.072** | 0.238 | 0.166 |
| Satisfacción con la democracia (negativa) | **0.092** | 0.108 | 0.192 |
| Importancia de la democracia (positiva) | **0.103** | 0.335 | 0.165 |

Le gana a los baselines en las tres, pero en la positiva solo 17.5% de las voces dice "muy importante" contra 61.6% de los colombianos. El permiso explícito para el entusiasmo fue un intercambio: la pregunta negativa mejor antes empeoró (0.056 → 0.072), el promedio apenas se movió (0.092 → 0.089); se conservó porque el rango entre preguntas se estrechó a la mitad (0.064 → 0.031). Decisión de consistencia, no de promedio.

### IRTree: probado y descartado

Pedir intensidad continua 0-100 y convertir a 1-5 con un árbol de respuesta al ítem (`scripts/experimento/irtree.py`, `careo_irtree.py`):

| | humanos | IRTree calibrado |
|---|---|---|
| media | 2.70 | 2.68 |
| desviación estándar | 1.07 | 1.08 (razón 1.01) |
| **W1** | — | **0.019** |

En la pregunta de calibración, casi calcado. **En la que nunca vio, W1 = 0.272 — peor que el azar.** Calibrar por pregunta es enseñarle al examen. El IRTree **no está en producción**; queda como resultado negativo documentado.

Por eso la app no reporta marginales como si fueran una medición: **los chequeos demográficos pasan 9/9 mientras las actitudes todavía fallan**. Dos defectos ya corregidos del experimento: señal de educación invertida (−0.148 → +0.32) y etiqueta de postura perdida (82% → 96.4%).

## 5. Lo que la literatura dice

- **Park et al. 2024** (arXiv:2411.10109): anclar agentes en datos individuales reales mejora la consistencia con el humano, pero el techo es la consistencia del propio humano consigo mismo. ColombIA se ancla en encuesta, no en entrevista larga.
- **Chen, Zhu & Zheng 2026** (arXiv:2607.26348): los modelos quedan 11–22 puntos bajo una regresión demográfica y sobredeterminan la identidad. Por eso aquí se mide la V de Cramér.
- **Argyle et al. 2023** (Political Analysis): acuña "algorithmic fidelity" y "silicon sampling"; ya condicionaba en historias de personas reales.
- **Bisbee et al. 2024** (Political Analysis 32(4)): las medias engañan; el 48% de los coeficientes de regresión difieren, con signo invertido el 32%. ⇒ **Nunca uses ColombIA para inferir qué causa qué.**
- **Santurkar et al. 2023** (ICML): el sesgo de RLHF persiste aunque le digas al modelo a qué grupo pertenece. Por eso el marco social es determinista, no lo "elige" el modelo.
- **Tao et al. 2024** (PNAS Nexus): los modelos se alinean con la Anglosfera; el cultural prompting explícito corrige en 71–81% de los países. Todo el andamiaje regional es cultural prompting.
- **González-Bustamante et al. 2025** (arXiv:2509.09871, caso chileno): el antecedente más cercano en la región. No existe trabajo publicado que ancle personas LLM en microdatos colombianos.

**Uso responsable (AAPOR 2026)**: las respuestas generadas no son participantes de investigación, deben identificarse como creadas por IA, no pueden llamarse "encuesta" ni "poll", y *no se puede producir margen de error de respuestas sintéticas*. La app lo dice en pantalla; los prompts son públicos.

## 6. Usos legítimos y prohibidos

**Sirve para**: explorar hipótesis antes de gastar en campo, pretest de preguntas, pedagogía sobre la estructura social colombiana, detectar subpoblaciones que merecen una encuesta real, divulgación.

**No sirve para**: reportar marginales como opinión pública, inferencia causal, estimar subgrupos pequeños, calcular márgenes de error.

**Prohibido explícitamente**: cualquier uso de targeting electoral o de campaña.

**Dos reglas que no se tocan**: el aviso de SIMULACIÓN nunca se quita, y no se acepta uso electoral.
## Sí/no: SSR contra categórico (22 sep 2026)

El sitio pregunta posturas, no escalas. Se midió con los 8 ítems de acuerdo de
la ECP (P5261S1-S8, Sí/No/No sabe; el "sí" real va del 4% al 86%), 120 voces por
condición, `deepseek/deepseek-v4.1-flash` por OpenRouter como en producción.
Métrica: error en puntos del % de "sí" entre quienes deciden.

| Condición | Categórico | SSR (anclas genéricas, T=0.25) |
|---|---|---|
| con libreto, calibración (S3 S4 S7 S8) | 13.4 | 11.8 |
| con libreto, prueba ciega (S1 S2 S5 S6) | 10.5 | 7.4 |
| sin libreto, calibración | 18.7 | 14.0 |

- SSR gana 5 de 8 ítems; no es significativo (signos, p≈0.7).
- Fallo estructural de SSR: en rechazos casi unánimes infla el "sí" ~20 pts
  (invadir propiedad: real 10.8%, SSR 30.4%, categórico 0%). Las negativas se
  dicen con vocabulario positivo y el embedding las acerca al ancla del "sí".
- Fallo del categórico: colapsa a 100% en consensos (mujeres: real 86%, 100%).
- Anclas que nombran la proposición: error 31-34 pts. Descartadas (negación).
- T se probó de 0.05 a 0.75 en la calibración: el óptimo es 0.25-0.35, el del
  paper; no se ajustó nada sobre la prueba ciega.
- **Libreto** (postura sorteada 40/40/20 por hash, igual para todo tema): el
  modelo lo ignora en temas de consenso; en los disputados empuja hacia 50/50.
  En la escala 1-5 (P5301), SSR da lo mismo con y sin él (W1 0.045 vs 0.050).

Decisión: SSR no se despliega en el sitio con esta evidencia. Siguiente prueba
necesaria: mezclar la etiqueta de postura de la propia voz con la distribución
SSR, medido en ítems nuevos.

Reproducir: `ENJAMBRE=sitio LIBRETO=1 node scripts/experimento/careo_ecp.mjs
120 P5261S1 x.json libre` y `uv run python scripts/experimento/postura.py x.json`.
