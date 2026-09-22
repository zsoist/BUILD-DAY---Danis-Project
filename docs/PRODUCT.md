# PRODUCT.md — ColombIA ¡Que Piensa!

## Qué es
Simulador de opinión pública colombiana. 8.000 personas sintéticas: personas reales encuestadas por el DANE en la GEIH (13 meses de microdatos), repesadas con proyecciones DANE 2026 y distribuidas en 33 departamentos (85 a 875 según población). Cada voz tiene edad, sexo, departamento, educación y estrato reales. El usuario elige un departamento o el país, escribe una pregunta en sus palabras, y las voces responden.

## Voces y validación
| Componente | Detalle |
|---|---|
| Modelo de voces | deepseek/deepseek-v4.1-flash vía OpenRouter; respaldo z-ai/glm-5.3-flash |
| Contra qué se comparan las respuestas | ECP 2023 del DANE (46.392 adultos reales). No es la fuente de las personas |
| Resultado | DeepSeek gana 3 de 5 preguntas y empata 2 contra la ECP |

## Para quién y cómo lo usa
| Usuario | Uso |
|---|---|
| Ciudadano curioso | Entra por enlace, pregunta, juega, se va. Sin registro. |
| Periodista / educador | Explora cómo variaría una opinión por región o perfil demográfico. |
| Constructor (dev) | Lee este doc y extiende encima, respetando la sección "qué NO es". |

Restricciones de diseño: una sesión dura segundos y cuesta poco por visita. Tope de gasto diario de 10 USD aplicado en el servidor. Nada que exija cuenta, instalación ni onboarding.

## Qué lo hace distinto
- Opinión cruzada con demografía real del DANE, no con una muestra genérica.
- Pregunta libre en lenguaje natural, no encuesta de opción múltiple.
- Fallos medidos y publicados, no escondidos (ver abajo).

## Qué NO es
- **NO es una encuesta.** No tiene margen de error. Prohibido reportar resultados como "el 38% de los colombianos" con pretensión de representación estadística.
- **NO sirve para campañas políticas ni segmentación de votantes.** Línea que no se cruza, sin excepciones.
- **Fallos conocidos, medidos y visibles:**
  | Fallo | Qué es | Estado |
  |---|---|---|
  | Sub-dispersión | Voces demasiado parecidas entre sí | Corregido con SSR: razón de desviación 0,77 → 0,98 (1,00 = ideal) |
  | Sesgo | GLM (el respaldo) ubica 38% en "muy insatisfecho" donde humanos ponen 18% | Medido; por eso GLM no es el principal |
  | Caricatura | La demografía predice opinión más de lo que predice en gente real | Medido, mitigable con contexto por voz |

- **IRTree: probado y rechazado.** Calibración W1 0,019, holdout 0,272: peor que el azar.
- Cualquier uso que dependa de precisión encuestística está fuera de alcance por diseño.

## Cómo sabemos si sirve
- Una persona nueva pregunta y entiende la respuesta en menos de 2 minutos, sin ayuda.
- Costo por sesión muy por debajo del tope diario de 10 USD bajo tráfico razonable.
- Métricas de calidad de simulación (sesgo, dispersión) reportadas junto a cada resultado, no en un anexo.
- La gente vuelve o comparte el enlace: señal de que jugó y le importó.

## Qué sigue
- Medir el sesgo de las voces principales en más preguntas de la ECP (hoy son 5).
- Reducir la caricatura agregando contexto no demográfico a cada voz.
- Panel visible por consulta con los fallos conocidos, para que nadie cite sin verlos.
