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
| **Caricatura: identidad→opinión (V de Cramér)** | **0.23** | 0.312 |

La última fila es la que más importa y viene de la crítica más dura a este campo:
los modelos **sobredeterminan** la opinión a partir de la identidad demográfica.
Nuestro andamiaje caricaturiza **menos** que el prompt desnudo, no más.

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
