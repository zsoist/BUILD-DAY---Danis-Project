# Candidatos de reto — Build Day

El evento premia: problemas reales que los modelos anteriores NO pudieron resolver,
con punto de comparación. Demo de 2 min: qué construiste, qué capacidad nueva usaste,
qué te sorprendió. La infra ya está: Fable orquesta 8 DeepSeek en paralelo.

## 1. Swarm-solver de problemas científicos (aprovecha la infra tal cual)
Dale a Fable un problema de mates/física que Opus 4 fallaba. Fable lo parte en
enfoques distintos (analítico, numérico, por contradicción, simulación), cada
DeepSeek-reasoner ataca uno, Fable cruza resultados y detecta el consenso/error.
**Demo fuerte:** mismo problema en un solo modelo vs. el enjambre, lado a lado.

## 2. Optimizador de costo/token del enjambre (con Jev — YA CABLEADO)
Jev (`typesafe/jev-1.13`, modelo de decisiones de TypeSafe en OpenRouter) ya está
integrado como gate del enjambre: juzga cada output con probabilidades calibradas
a ~$0.00002/llamada. Meta-capa posible: Fable usa los scores de Jev del log
(`runs/*.jsonl`, evento `jev`) para re-balancear el siguiente plan — menos agentes,
thinking más bajo donde Jev aprueba fácil, high solo donde falla. **Demo fuerte:**
curva de costo bajando ronda a ronda con calidad igual, medida por un juez neutral.

## 3. Migrador/actualizador masivo de repos
Fable planifica la migración de un repo real (deps viejas, API changes), workers
DeepSeek parchean archivos en paralelo, Fable revisa diffs y corre tests.
**Demo fuerte:** repo que no compilaba → verde en una sesión.

## Recomendación
La #1 es la más alineada con el público del evento (científicos, alta complejidad)
y usa el orquestador sin cambios. La #2 es el mejor "wow" de ingeniería si sobra
tiempo: se monta encima de la #1.
