# ColombIA ¡Que Piensa! — Método, alcance y límites

> **Qué es esto**: un simulador de población colombiana. Cada residente toma sus
> variables socioeconómicas de una **persona real encuestada por el DANE** (GEIH
> 2025 – jul 2026) y recibe un nombre y una personalidad **generados**. Las
> opiniones que verás las produce un modelo de lenguaje.
>
> **Qué NO es**: una encuesta. No mide opinión pública colombiana. No tiene
> margen de error. Ninguno de estos residentes existe.

---

## 1. De dónde sale cada cosa

| Capa | Fuente | Naturaleza |
|---|---|---|
| Edad, sexo, educación, oficio (CIUO-08), ingreso laboral, régimen de salud, urbano/rural | **Microdatos GEIH** del DANE, 13 meses (2025 – jul 2026), 884.034 personas | **Real**, muestreada conjuntamente (no variable por variable) |
| Peso de expansión | `FEX_C18` de la GEIH | **Real** |
| Población, pirámide de edad, % urbano por departamento | Proyecciones DANE 2026 | **Real** |
| Pobreza monetaria, Gini, PIB sectorial | Anexos oficiales DANE 2025 | **Real** |
| Inclinación política territorial | Senado 2018 a nivel de **mesa** (datos.gov.co) | **Real**, agregada por departamento |
| Nombre, apellido, retrato | Generados a partir de frecuencias regionales | **Sintético** |
| Temperamento, franqueza, arranque, marco social, fundamento | **Deterministas por hash del id** — el mismo residente es siempre igual | **Sintético** |
| Lo que dice | Modelo de lenguaje (DeepSeek) con el prompt del residente | **Generado** |

El muestreo es **conjunto**: no se sortea "una edad" y luego "un oficio" por
separado, sino que se toma una persona GEIH completa. Eso preserva las
combinaciones que existen de verdad (un agricultor de 60 años sin bachillerato
en zona rural del Cauca) y evita los quimeras de los métodos marginales.

### Sesgo de cobertura documentado
La GEIH **solo encuesta cabeceras** en Amazonas, Guainía, Vaupés y Vichada. Sin
corrección, esos departamentos salían 100% urbanos. Se imputa la cuota rural del
marginal DANE priorizando perfiles rural-plausibles, de forma determinista y
documentada en `simcolombia/pipeline/generate_population_v2.py`.

---

## 2. Qué se valida y cómo (9 chequeos deterministas)

`simcolombia/pipeline/validar_v2.py` corre en cada regeneración y falla la build
si algo se sale de banda. **Ninguna cifra la juzga un modelo de lenguaje.**

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

---

## 3. ¿Y las voces? El experimento A/B

La pregunta "¿suenan a personas reales?" no se responde opinando. Se corre
`scripts/experimento/` : los **mismos residentes** contestan la **misma pregunta**
dos veces — con el andamiaje completo (A) y con un prompt desnudo de control (B) —
y se miden diferencias en Python sobre el texto crudo.

Resultado (n=28, subsidio a jóvenes que ni estudian ni trabajan):

| Métrica | A (andamiaje) | B (control) |
|---|---|---|
| Diversidad léxica | **26.1%** | 24.5% |
| Arranques distintos | **85.7%** | 67.9% |
| Variación de largo (CV) | **0.333** | 0.179 |
| Señal de educación (r) | **+0.32** | +0.07 |
| Índice de manada (4-gramas propios) | **0.49** | 0.61 |

### La prueba de caricatura, contra colombianos de verdad

La crítica más dura a este campo es que los modelos **sobredeterminan**: tratan la
identidad demográfica como mucho más predictiva de la opinión de lo que es. Para
saber si nos pasa, hace falta un patrón humano. Lo sacamos de la **Encuesta de
Cultura Política del DANE** (`scripts/experimento/baseline_ecp.py`), la misma casa
que produce la GEIH:

**Colombianos reales — ECP 2023, n=46.392 adultos, 68 preguntas actitudinales**
(V de Cramér, mediana): edad **0.048** · educación **0.071** · sexo **0.021**.
Es decir: en la gente real, saber tu edad casi no permite adivinar tu opinión.

**Nuestras voces vs. el control desnudo** (n=160 residentes, misma pregunta, con
prueba de permutación de 1.500 barajadas para descartar el azar):

| Atributo | A · andamiaje | B · control desnudo |
|---|---|---|
| edad → postura | 0.104 (p=0.86, **azar**) | 0.256 (p=0.002, **señal real**) |
| educación → postura | 0.093 (p=0.71, azar) | 0.133 (p=0.26, azar) |
| sexo → postura | 0.016 (p=1.00, azar) | 0.224 (p=0.023, **señal real**) |

**El prompt desnudo sí caricaturiza** — inventa una relación entre edad/sexo y
opinión que en Colombia no existe. Con el andamiaje completo, ninguna asociación
se distingue del azar, y los valores caen en el rango de los humanos reales.

> **Corrección honesta**: una versión anterior de este documento reportaba
> "0.23 vs 0.312" a favor del andamiaje con n=28. Al correr la prueba de
> permutación, ese n daba una V de azar de 0.275 — la cifra medía ruido, no
> señal. Se repitió con n=160 y control de azar. El resultado de arriba es el
> bueno; el anterior no debió publicarse sin el test.

**Lo que todavía falla**: el 19% de las respuestas pierde la etiqueta de postura,
y en este tema la distribución quedó muy de un lado (65% en contra, 5% a favor)
frente a un control mucho más repartido. Que la demografía no mande no garantiza
que la distribución global sea la del país.

---

## 4. El careo: la misma pregunta del DANE, a sintéticos y a humanos

Esta es la prueba que la literatura pide y que, hasta donde alcanza nuestra
revisión, **nadie había hecho con microdatos colombianos**. Tomamos la pregunta
**literal** de la Encuesta de Cultura Política 2023 sobre satisfacción con la
democracia (escala 1-5), se la hicimos a 200 residentes sintéticos, y comparamos
contra las respuestas humanas reales ponderadas con el factor de expansión
oficial del DANE (`scripts/experimento/careo_ecp.mjs` + `.py`).

**El resultado fue un suspenso, y es el hallazgo más importante del proyecto:**

| Opción | Colombianos reales | Sintéticos (antes) | Sintéticos (después) |
|---|---|---|---|
| 1 muy insatisfecho | 18.1% | 42.7% | 3.0% |
| 2 insatisfecho | 17.0% | 51.3% | 60.3% |
| **3 ni una ni otra** | **46.0%** | **6.0%** | **36.7%** |
| 4 satisfecho | 14.0% | 0.0% | 0.0% |
| 5 muy satisfecho | 4.8% | 0.0% | 0.0% |
| media de la escala | 2.70 | 1.63 | 2.34 |
| **W1 normalizado** | — | **0.268 (lejos)** | **0.168 (aceptable)** |

**Diagnóstico**: nuestros colombianos sintéticos estaban mucho más furiosos que
los de carne y hueso. La respuesta más común del país — el punto medio, el "ahí
vamos" — casi no existía, porque el prompt empujaba a todo el mundo a tomar
partido y a quejarse. Corregido con una regla explícita: *en una escala de
encuesta el punto medio es legítimo y mayoritario*. La media pasó de 1.63 a 2.34
(real: 2.70) y el punto medio de 6% a 36.7%.

### La sub-dispersión, atacada con psicometría

La sub-dispersión (razón de desviación 0.50 cuando el objetivo es 1.0) es el
fallo que Bisbee et al. documentan como central: las voces sintéticas opinan más
parecido entre sí que la gente real. La hipótesis que probamos no viene de la
literatura de IA sino de la **psicometría clásica**: las personas reales no usan
una escala de la misma manera. Existe el *estilo de respuesta extremo*, el que
evita los extremos, el benévolo y el que se refugia en el "no sé". Si todos
nuestros residentes usan la escala igual, la dispersión colapsa por construcción.

Se le dio a cada residente un estilo de respuesta determinista por hash
(`estiloRespuesta()`), sin decirle nunca al modelo cuál es la distribución
objetivo — eso habría sido enseñarle al examen e invalidado la medición.

| | W1 normalizado | razón de SD | punto medio |
|---|---|---|---|
| antes de todo | 0.268 (lejos) | 0.50 | 6.0% |
| con la regla de tibieza | 0.168 | 0.50 | 36.7% |
| **+ estilo de respuesta** | **0.099 (cerca)** | **0.79** | **49.0%** (real: 46.0%) |

**Y generaliza**: validado en una pregunta *que nunca se tocó* — eficacia
política (`P3573`, "¿hasta qué punto el sistema político permite que personas
como usted tengan voz y voto?"): **W1 = 0.056**, razón de SD **0.83**, media
2.23 frente a 2.05 real. Mejor aún que en la pregunta contra la que se afinó,
que es exactamente lo que uno quiere ver para descartar sobreajuste.

**Lo que sigue roto**: casi nadie elige el extremo positivo (2% dice
"satisfecho" frente al 14% real) y nadie dice "no sé" (0% frente a 4.2%). La
resistencia del modelo al lado amable es profunda y el prompt no la mueve; la
literatura sobre colapso de modo sugiere que vive en los pesos.

### ¿Le gana a no hacer nada? El control que casi nadie reporta

Un W1 bajo no significa nada por sí solo: hay que saber qué saca alguien que no
simula nada. El medidor ahora imprime dos baselines triviales — "todos contestan
al azar" y "todos contestan lo más común":

| Pregunta | Simulador | Azar | Lo más común | ¿Gana? |
|---|---|---|---|---|
| Satisfacción con la democracia (afinada) | **0.099** | 0.108 | 0.192 | sí, **por poco** |
| Eficacia política (sin tocar) | **0.056** | 0.238 | 0.166 | sí, **con holgura** |

Dicho sin adornos: en la pregunta contra la que afinamos, el simulador apenas le
gana al azar; en la que nunca tocamos, le gana con claridad. Esa asimetría es
información honesta sobre dónde estamos, y es el tipo de control que la
literatura exige y que la mayoría de los trabajos del sector omite.
- **Nadie está satisfecho**: 0% elige 4 o 5, cuando el 18.8% de los colombianos
  sí lo hace.
- **Nadie dice "no sé"**: 0% frente al 4.2% real.

Por eso la app no reporta marginales de opinión como si fueran una medición, y
por eso este documento existe: **los chequeos demográficos pasan 9/9 mientras las
actitudes todavía fallan**. Una demo que solo muestre pirámides cuadradas no
prueba nada — exactamente la advertencia de Bisbee et al.

Dos defectos que el experimento encontró y que ya se corrigieron:
- La señal de educación estaba **invertida** (−0.148): el prompt aplanaba el
  registro de los más educados. Corregido → +0.32.
- La etiqueta de postura se perdía. Mover el recordatorio al turno de usuario
  la subió de **82% a 96.4%** (medido, no supuesto).

---

## 4. Lo que la literatura dice, y dónde nos deja

Hallazgos verificados en fuente primaria:

- **Park et al. 2024** (*Generative Agent Simulations of 1,000 People*,
  arXiv:2411.10109): agentes anclados en una **entrevista real** alcanzan 83% del
  techo de consistencia test-retest del propio humano; con **solo demografía**,
  74%. Anclar en datos individuales reales compra ~**+8 a +12 puntos**.
  **Matiz honesto**: ColombIA no tiene dos horas de entrevista por persona, así
  que se parece a la condición *encuesta sola* (**82%**), no a la de entrevista.
  La ganancia del anclaje es real pero moderada, no transformadora. Y el techo
  de ese 82% no es "la verdad": es la consistencia del propio humano consigo
  mismo dos semanas después.
- **Chen, Zhu & Zheng 2026** (arXiv:2607.26348): en la World Values Survey los
  modelos quedan **11 a 22 puntos por debajo de una simple regresión
  demográfica**, y sobredeterminan la identidad (la ideología explicaba ~1.5%
  de la varianza en humanos y hasta 67% en los modelos). Por eso aquí se mide
  la V de Cramér: para vigilar que la identidad no decida la opinión.
- **Argyle et al. 2023** (*Out of One, Many*, Political Analysis): acuña
  "algorithmic fidelity" y "silicon sampling"; ya condicionaba en historias de
  personas reales. La tradición metodológica es correcta.
- **Bisbee et al. 2024** (*The Perils of Large Language Models*, Political
  Analysis 32(4)): **las medias engañan**. La varianza sintética colapsa, y el
  **48%** de los coeficientes de regresión difieren de los reales, con el **signo
  invertido el 32%** de las veces. ⇒ **Nunca uses ColombIA para inferir qué causa
  qué.**
- **Santurkar et al. 2023** (*Whose Opinions Do Language Models Reflect?*, ICML):
  los modelos con RLHF tiran a progresista, y **el sesgo persiste aunque le
  digas al modelo a qué grupo pertenece**. Por eso aquí la postura en temas
  morales la fija un **marco social determinista** calibrado por edad, educación
  y ruralidad — no la "elige" el modelo.
- **Tao et al. 2024** (*Cultural bias and cultural alignment of LLMs*, PNAS
  Nexus 3(9)): por defecto los modelos se alinean con la Anglosfera; el
  **"cultural prompting"** explícito mejora la alineación en 71–81% de los
  países. Todo el andamiaje regional de ColombIA es cultural prompting.
- **González-Bustamante et al. 2025** (arXiv:2509.09871, caso chileno): el
  antecedente más cercano en la región. Hasta donde alcanza esta revisión, **no
  existe trabajo publicado que ancle personas LLM en microdatos colombianos**.

### Uso responsable (estándar AAPOR 2026)
La *AAPOR Task Force on Responsible AI Integration in Survey Research* (mayo
2026) es explícita: las respuestas generadas **no son participantes de
investigación**, deben identificarse como creadas por IA, y **no deben llamarse
"encuesta" ni "poll"**; además, *"a margin of error cannot be produced from
synthetic responses"*. Por eso la app lo dice en pantalla, los prompts están en
este repositorio público, y el banner nombra la fuente humana que ancla a los
residentes.

---

## 5. Usos legítimos y usos prohibidos

**Sirve para**: explorar hipótesis antes de gastar en campo, pretest de
preguntas, pedagogía sobre la estructura social colombiana, detectar
subpoblaciones que merecen una encuesta real, y divulgación.

**No sirve — y no se debe usar — para**: reportar marginales como si fueran
opinión pública, inferencia causal, estimar subgrupos pequeños, calcular márgenes
de error.

**Prohibido explícitamente por los dueños de este proyecto**: cualquier uso de
targeting electoral o de campaña. La evidencia de sesgo político de los modelos,
de ruptura de las relaciones estadísticas y de caricaturización de grupos
marginalizados hace de ese uso un mecanismo de daño, no una herramienta.

**Dos reglas que no se tocan**: el aviso de SIMULACIÓN nunca se quita, y no se
acepta uso electoral.
