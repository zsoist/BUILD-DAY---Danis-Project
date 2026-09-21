# El papel de Fable 5.1 — qué hacemos con los $100

Diseñado sobre la literatura real (Generative Agents/Park 2024, Argyle "silicon
sampling", los papers de Perils que miden 7x de polarización inflada, el caso
chileno 2025 con 189k perfiles, Hidden Anchors, AgentSociety). La conclusión del
estado del arte: lo menos explorado y más defendible NO es que el modelo grande
actúe de títere más fino — es que actúe de **científico que audita la simulación**.

## El arco de la demo: "Fable como encuestado, juez y sociólogo"

### Acto 1 — EL AUDITOR (~$50) ⭐ el plato fuerte
Encuestamos con Fable 5.1 una submuestra estratificada (~1.500-2.000 residentes,
10 preguntas por llamada, JSON forzado) con preguntas que TIENEN verdad publicada:
Latinobarómetro Colombia (confianza en instituciones, satisfacción con la
democracia, economía) + Pulso Social del DANE. Comparamos marginales sintéticos
vs. reales por celda (sexo × edad × educación × región) → **mapa de calor del
sesgo**: a qué colombianos representa mal el modelo (predicción de la literatura:
rurales, mayores, baja educación; polarización inflada). Luego Fable, como
auditor, escribe el "informe del sociólogo" con los modos de fallo nombrados y
citados. Es la metodología del caso chileno aplicada por primera vez a Colombia.

### Acto 2 — FORENSE DE DELIBERACIONES (~$20)
Nuestro activo único: TODAS las tertulias quedan logueadas (sim_encuestas).
Fable puntúa por turno: fidelidad al personaje, trayectoria de postura (1-7),
convergencia sicofante (dar la razón sin argumento nuevo) vs. cambio con
argumento. Métricas contra lo que la literatura dice de humanos deliberando
(America in One Room: actualización modesta y asimétrica, no colapso a consenso).
Titular probable: "hasta nuestra mejor simulación es demasiado complaciente —
y solo un modelo frontier lo detecta".

### Acto 3 — DOS FUTUROS (~$25, si alcanza la noche)
Una política viva (tarifa del metro, reforma pensional): los mismos 300
residentes bajo encuadre A vs. B; Fable calcula efectos heterogéneos por celda
demográfica y escribe el informe con citas en la voz de cada región. Se presenta
como GENERACIÓN DE HIPÓTESIS, citando nosotros mismos los límites (Perils) —
la autocrítica en escena es rigor, no debilidad.

### Reserva: ~$5-10.

## Por qué esto gana
- Es el track Breakthrough literal: tareas que un modelo pequeño hace mal
  (juez calibrado, consistencia de persona larga, informe estructurado).
- Verificabilidad como feature (patrón de Tekton, 1° puesto): cada número del
  sim es DANE, cada juicio de Fable trae la cita del turno que lo prueba.
- La demo se narra sola: el país sintético responde → Fable te dice DÓNDE miente
  → y lo corrige delante del público.

## Pendientes pre-evento
- [ ] Bajar marginales de 3-5 preguntas de Latinobarómetro 2024 Colombia (CSV).
- [ ] Script `fable_auditor.py`: encuesta estratificada batcheada + heatmap.
- [ ] Script `fable_forense.py`: lee sim_encuestas y puntúa turnos.
- [ ] `FABLE_ENABLED=1` + workspace ya verificado (wrkspc_01GN…).
