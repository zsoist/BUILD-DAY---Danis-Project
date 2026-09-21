# EL PROGRAMA DE LOS $100 — Fable 5.1 sobre Sim Colombia (v2 definitiva)

Datos duros del lanzamiento (verificados hoy): 1M de contexto, output 128K,
$10/$50 por Mtok, **cache reads a $0.25/Mtok (–75%)**, thinking adaptativo con
dial de esfuerzo (low→max), campeón en trabajo agéntico largo (Terminal-Bench-
Science ×2 vs Fable 5; sim de negocio de 30 días; sim de vida de 5 personajes
en un solo prompt). Sin benchmark publicado de juez/calibración → nosotros lo
medimos en escena (eso ES contenido).

## ACTO 0 — "FABLE SE LEE A COLOMBIA ENTERA" (~$12) ⭐ la jugada imposible

El movimiento que SOLO un modelo de 1M puede hacer y solo con cache-reads
baratos tiene sentido económico: serializamos EL PAÍS COMPLETO en un contexto
(~600-800K tokens): los 6.600 residentes, los 33 dossiers y voces, los
marginales DANE con fuentes, y TODAS las tertulias/mesas/sondeos de hoy
(sim_encuestas). Se paga una vez (~$7) y queda CACHEADO: cada pregunta
siguiente relee el país entero por ~$0.20.

Y entonces lo interrogamos delante del público, pregunta tras pregunta:
- "Encuentra las 10 personas menos verosímiles del país y demuéstralo."
- "¿Dónde traiciona el muestreo al censo? Cita celda y número."
- "¿Qué contradicciones internas tiene este país?" 
- "Escribe el informe del sociólogo: qué le duele a esta Colombia, con citas."

**El pitch:** "Ningún modelo por debajo de esta ventana puede sostener un país
en la cabeza. Fable se lo leyó COMPLETO — y ahora respondan lo que quieran."

## ACTO 1 — EL AUDITOR (~$35)

Silicon-poll estratificado (~1.200 residentes, 10 preguntas/llamada, effort
medium) con preguntas que tienen verdad publicada (Latinobarómetro Colombia +
Pulso Social DANE) → mapa de calor del sesgo por celda (sexo×edad×educación×
región) → Fable (effort max) escribe el veredicto con evidencia. Metodología
del caso chileno 2025, primera vez para Colombia. Predicción a confirmar:
falla más con rurales, mayores y baja educación.

## ACTO 2 — EL FORENSE (~$15)

Sobre el corpus YA cacheado del Acto 0: Fable puntúa las deliberaciones de hoy
turno a turno — ¿cambios de opinión por argumento o por complacencia?
¿convergencia más rápida que los humanos de America in One Room? ¿anclaje?
Barato porque relee caché. Titular esperado: "nuestra Colombia es demasiado
amable — y solo un frontier lo ve".

## ACTO 3 — COLOMBIA 2050 (~$18) ⭐ el viaje en el tiempo

El archivo DANE que ya tenemos llega hasta 2050. Regeneramos la población con
la pirámide de 2050 (un país MUCHO más viejo: la transición demográfica real)
y le hacemos LAS MISMAS preguntas de esta noche a las dos Colombias. Fable
(effort high) analiza el corrimiento: qué opinión envejece, cuál resiste.
**"Le preguntamos al futuro — con los datos oficiales del futuro."**
(Pipeline listo: `AÑO_SIM=2050` en build_marginals + regenerar. 10 minutos.)

## ACTO 4 — EL DIRECTOR DE ORQUESTA (~$5, teatral)

`FABLE_ENABLED=1`: Fable toma el mando del ejército en vivo con el visor
proyectado — General de verdad por primera vez. Una misión corta.

## Reserva: ~$15. · Total estimado: ~$85 + reserva.

## Notas de operación (del system card)
- Turnos LARGOS (minutos): stream siempre; effort dial por acto (medium para
  encuestas masivas, max para veredictos).
- Sin tool_choice forzado; manejar stop reason `refusal` con reintento suave.
- El juez-Fable no tiene benchmark publicado de calibración → mostramos
  spot-checks humanos en escena (rigor visible = puntos).

## El cierre de la demo (2 minutos)
"Esta mañana no existía nada de esto. Un ejército de agentes de $0.15/M
construyó un país con el censo real y lo puso a discutir con noticias reales.
Esta noche, el modelo más potente de Anthropic se leyó ese país ENTERO de una
sentada, nos dijo dónde miente, cómo delibera mal, y qué opinará cuando
envejezca. Eso es hasta dónde llega el modelo."
