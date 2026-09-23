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
| Gente | 144 personajes generados (12 regiones), cada uno con 8 cuadros: quieto, dos pasos de frente, mano arriba, dos de lado (a la izquierda se refleja), dos de espaldas (`scripts/escena/direcciones.py`). El cuadro lo elige la dirección en que camina. Se asignan por región, sexo, edad y oficio. Escalados sin suavizado (`NearestFilter`) |
| Escenarios | Fondos generados, sin personas, con el tercio inferior libre para la mesa. Uno por región; `estudio` para el sondeo |
| Cielo y ambiente | El cielo pálido se recorta (`scripts/escena/cielo.py`) y se pinta uno pixel vivo: tramado Bayer, nubes, pájaros del lugar. Animales, vehículos y transeúntes (`escenas/amb/`) solo si tienen sentido ahí; sus carriles se miden sobre la imagen (`AMB` en `escena.js`) |
| Movimiento | La gente camina a su silla con sus cuadros de paso y levanta la mano al empezar a hablar. Nada se mueve sin motivo; `prefers-reduced-motion` apaga el caminar y la cámara |
| Piso | Cada fondo tiene su línea de piso (`SUELO` en `escena.js`, medida sobre la imagen): nadie se para, pasea ni entra por encima de ella (casas, muros, río, cielo). Se entra por el fondo de la calle o por las orillas del piso. Fondo nuevo = medir su línea |
| Reparto | Hasta 9: herradura detrás de la mesa, pareja en x (nadie tapa a nadie). Más: la mesa con 7 y corrillos al fondo; los nombres solo de quien habla o al pasar el mouse |
| Cámara | 2D sobre el diorama entero (`#mundo`): nunca mover la cámara 3D sola, se desalinea del piso pintado. Se acerca a quien habla (más con mucha gente); rueda, arrastre y doble clic a mano. Con más de 9, fondo panorámico (2048×896): el mundo es más ancho que la ventana y la cámara lo recorre, entrando desde la izquierda |
| Verdad | Cada vista dice si hay dato real detrás (📊) o es exploración (🧭). El aviso de SIMULACIÓN no se quita nunca |

## Tokens

```css
--noche:#0b1030; --win-a:#2a3a8f; --win-b:#121a4a; --crema:#f4ecd8;
--oro:#fcd116; --si:#2fd08a; --no:#ff5a5f; --dep:#fcd116; --nini:#9aa3b8;
--tinta:#f4ecd8; --tenue:#b9c0e0;
```
