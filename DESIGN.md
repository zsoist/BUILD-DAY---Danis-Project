# DESIGN.md — ColombIA ¡Que Piensa!

Mundo: **HD-2D colombiano**. Dioramas en pixel art de lugares reales del país
(Plaza de Bolívar, la muralla de Cartagena, la Comuna 13, Cocora, el Atrato…),
con luz cálida, niebla y profundidad; la gente es sprite pixel nítido, de pie en
un espacio 3D. La interfaz es la de un JRPG de consola: ventanas de diálogo.

## Reglas durables

| Qué | Regla |
|---|---|
| Composición | El **escenario** manda: ocupa el viewport. El **chat** es una ventana al lado (abajo en móvil). Mapa, censo y "la tierra" son **ventanas desplegables**, nunca columnas fijas |
| Ventana | Fondo añil en degradado vertical (`--win-a` → `--win-b`), borde doble crema (2px + 2px con 2px de aire), esquinas de 6px. Es el único contenedor: no hay tarjetas grises |
| Cursor | ▶ amarillo bandera (`--oro`) marca foco, selección y el turno de quien habla |
| Letra | Silkscreen para rótulos, nombres y botones (mayúsculas, con sombra dura 2px). Saira para lo que se lee |
| Posturas | sí = esmeralda `--si`, no = rojo `--no`, depende = oro `--dep`, ni fu ni fa = gris `--nini`. Nunca otro significado para estos colores |
| Gente | Sprites procedurales desde la ficha DANE (sexo, edad, oficio, región): 24×40 px, escalados sin suavizado (`image-rendering: pixelated`, `NearestFilter`) |
| Escenarios | Fondos generados, sin personas, con el tercio inferior libre para la mesa. Uno por región; `estudio` para el sondeo |
| Movimiento | La gente camina a su silla, rebota al hablar, la cámara se acerca un poco a quien habla. Nada se mueve sin motivo; `prefers-reduced-motion` apaga el caminar y la cámara |
| Verdad | Cada vista dice si hay dato real detrás (📊) o es exploración (🧭). El aviso de SIMULACIÓN no se quita nunca |

## Tokens

```css
--noche:#0b1030; --win-a:#2a3a8f; --win-b:#121a4a; --crema:#f4ecd8;
--oro:#fcd116; --si:#2fd08a; --no:#ff5a5f; --dep:#fcd116; --nini:#9aa3b8;
--tinta:#f4ecd8; --tenue:#b9c0e0;
```
