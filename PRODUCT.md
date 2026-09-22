# PRODUCT.md — ColombIA ¡Que Piensa!

## Qué es
Simulador de opinión pública colombiana. 47.000 personas sintéticas construidas sobre microdatos del DANE (censo + Encuesta de Cultura Política 2023, 46.392 adultos). Cada voz tiene edad, sexo, departamento, educación y estrato reales en proporción. El usuario elige un departamento o el país, escribe una pregunta en sus palabras, y las voces responden.

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
  | Sesgo | Modelo corrido: GLM ubica 38% en "muy insatisfecho" donde humanos ponen 18% | Medido, pendiente mitigar |
  | Caricatura | La demografía predice opinión más de lo que predice en gente real | Medido, mitigable con contexto por voz |

Cualquier uso que dependa de precisión encuestística está fuera de alcance por diseño.

## Cómo sabemos si sirve
- Una persona nueva pregunta y entiende la respuesta en menos de 2 minutos, sin ayuda.
- Costo por sesión muy por debajo del tope diario de 10 USD bajo tráfico razonable.
- Métricas de calidad de simulación (sesgo, dispersión) reportadas junto a cada resultado, no en un anexo.
- La gente vuelve o comparte el enlace: señal de que jugó y le importó.

## Qué sigue
- Mitigar el sesgo del GLM (38% vs 18% en "muy insatisfecho").
- Reducir la caricatura agregando contexto no demográfico a cada voz.
- Panel visible por consulta con los fallos conocidos, para que nadie cite sin verlos.