# Cómo leer lo que hizo tu enjambre

Abriste el visor y hay colores, líneas y barras por todas partes. Te explico cómo pasar de mirar a entender.

## El recorrido de una tarea

Toda tarea sigue el mismo camino. Primero alguien la **planifica**: se descompone en piezas que se puedan hacer por separado. Luego esas piezas se **reparten** entre los trabajadores del enjambre. Los trabajadores **ejecutan en paralelo**: varios trabajan al mismo tiempo, cada uno en lo suyo. Cuando terminan, el **inspector** revisa el resultado: ¿está bien hecho, cumple lo que pedía la pieza? Y al final, el **ensamblador** junta todas las piezas revisadas en el resultado único que tú querías.

En el visor esto se ve como una lista de tareas con estados. Si una tarea está "en ejecución", un trabajador la tiene entre manos. Si está "en revisión", el inspector la está evaluando. Si ya dice "completada", pasó la revisión y el ensamblador la tiene disponible.

## Los veredictos del inspector

El inspector no solo dice sí o no. Puede dar cuatro veredictos, y cada uno desencadena algo distinto:

- **Aprobado.** El trabajo está bien. La tarea queda lista para el ensamblador y nadie la toca más. Es el final feliz.
- **Corregir con notas.** El trabajo está casi bien, pero el inspector dejó comentarios concretos: qué falta, qué está mal. La tarea vuelve al mismo trabajador con esas notas a mano. Suele resolverse rápido, porque el trabajador ya tenía el contexto.
- **Reintentar pensando más.** El inspector detecta que el problema no fue de ejecución sino de razonamiento: el enfoque estaba mal desde el inicio. La tarea vuelve a empezar, pero esta vez el trabajador dedica más esfuerzo a planificar antes de escribir. Es más lento que una corrección con notas, pero evita parches sobre una base torcida.
- **Escalar a un modelo mayor.** El inspector concluye que la tarea es demasiado difícil para quien la tenía. Se reasigna a un modelo más capaz (y más caro y lento). Si ves esto en el visor, significa que el enjambre se dio cuenta solo de que necesitaba refuerzos.

## Leer el paralelismo

La línea de tiempo es donde se ve la magia. Cada tarea es una barra horizontal: empieza en un momento y termina en otro. Cuando dos barras **se solapan**, significa que esas tareas se ejecutaron **al mismo tiempo**, en trabajadores distintos.

Ahí está el ahorro de tiempo. Si tenías diez tareas y seis se solapan durante un tramo, el enjambre hizo en ese tramo el trabajo de seis a la vez. Cuanto más se solapan las barras, menos tiempo total tardó todo. Una línea de tiempo con barras escalonadas una detrás de otra es señal de que el enjambre trabajó en serie: funcional, pero lento.

## Leer las dependencias

No todo puede ir en paralelo. Algunas tareas **dependen** de otras: no pueden empezar hasta que otra termine. Por ejemplo, no puedes ensamblar el documento final hasta que todas las secciones estén escritas y aprobadas.

En el visor, las dependencias se ven como flechas o conexiones entre tareas, y como barras que no pueden arrancar antes: la tarea espera con estado "bloqueada" o "pendiente" mientras su predecesora trabaja.

Conviene que haya **pocas dependencias**. Cada dependencia es un cuello de botella potencial: si la tarea de la que otros dependen se demora o falla, arrastra a todas las que esperaban detrás. Un buen plan maximiza las tareas independientes (que pueden ir en paralelo) y minimiza las cadenas de espera. Si ves muchas flechas encadenadas, el planificador pudo haber repartido mejor.

## Cuando algo salió mal

Si una tarea terminó mal o tardó demasiado, lo primero que hay que mirar es el **número de intentos**. Cada tarea lleva un contador: cuántas veces pasó por el ciclo ejecutar-revisar antes de quedar lista (o de rendirse).

Una tarea con **un intento** es normal: salió bien a la primera. Dos intentos también es razonable: una corrección con notas y listo. Pero una tarea que necesitó **tres intentos** cuenta una historia: algo en esa tarea es intrínsecamente difícil, o el enunciado era ambiguo, o el trabajador se estancó en el mismo error repetidas veces. Fíjate también en qué veredictos recibió: tres "corregir con notas" es distinto de "reintentar pensando más" dos veces y luego escalar. La secuencia de veredictos te dice si el problema era de pulido fino o de enfoque.

En resumen: solapa bueno, dependencias pocas, intentos pocos. Todo lo demás, el enjambre lo maneja.