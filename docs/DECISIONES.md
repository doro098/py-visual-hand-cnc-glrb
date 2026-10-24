# Decisiones

## Proyecto aparte, no un branch

Es otro objetivo con la misma plataforma. py-visual-hands brilla con los
gestos y la ventana animada; acá lo que gobierna es un lazo de control: la
menor complejidad posible entre "veo la mano desplazada" y "muevo el eje".
Hubiese sido doloroso mantener esa baja complejidad dentro de un repo con
4 motores, dataset de gestos y entrenamiento.

## GRBL (gnea/grbl v1.1) como firmware de los ejes

Los dos motores paso a paso bajan a un Arduino Uno con shield GRBL. GRBL
trae resuelto todo lo que en un brazo real importa y es aburrido de
reescribir: generación de pulsos por timer, aceleración trapezoidal,
límites y feed. Y mantiene el Uno como única pieza de firmware propia del
proyecto: flashear y configurar `$100-$121`, nada más.

## Jog incremental (`$J=G91 ...`) y no G1 posicional

El lazo no sabe la posición final de la mano: solo la velocidad que ahorita
conviene. Un jog incremental corto (un frame de duración, dt sujeto a
0.02–0.06 s según el cálculo de latencia de la wiki) expresa exactamente
eso, no toca el parser modal de G-code y GRBL lo acepta en Idle/Jog con
`ok` por comando. Cada jog queda pendiente de ack antes de mandar el
siguiente: el planner nunca arrastra cola y la latencia es la mínima
posible para este hardware.

## El freno es el byte realtime 0x85

Si la mano se pierde, se pausa o se sale, cancelar el jog con 0x85 corta el
movimiento y vacía lo que haya en la cola, sin soft-reset y sin tocar el
parser. Es el failsafe barato: un byte.

## Modo seco por defecto

Sin `--serial` no se abre puerto: los `$J=` se imprimen. Así el lazo
completo (motor, centro, PID, gráfico) se prueba con la cámara sola, y los
tests no necesitan ni cámara ni hardware: el canal Seco graba lo mandado.

## PID puro y testeado

`pid.Pid` no permite numpy ni puertos: entra error, sale mm/s. Es la única
pieza con estado del lazo, así que es la que merece tests con errores
fabricados (zona muerta, anti-windup, signo, tope). El resto del proyecto
es pegamento.

## Ancla: centro de la palma (0, 5, 17)

Promedio de muñeca y de las dos bases de dedos periféricos. La punta del
índice tiembla y a veces se cruza con la nariz; la palma es el punto que
la cámara de verdad sostiene cuando "está enfocada a la mano".

## `num_manos=1`

El lazo solo puede perseguir un blanco: trackear dos manos es el doble de
inference para nada y fuentes de renegar (¿cuál sigue?). La mano que se ve
primero, es.

## Qué se tiró de py-visual-hands

`gestos`, `reglas` y `custom` como motores; `capturar.py`, `entrenar.py`,
`descargar_modelos.py` de 2 checkpoints (queda 1); `NOMBRES_GESTOS`; el
dataset y el gulp de entrenamiento. Viven en el otro repo.

## Qué falta (calibración real)

Los defaults del PID (kp 60 / ki 8 / kd 0, vmax 30 mm/s, feed 600 mm/min)
son plausibles, no probados: se ajustan con el brazo enfrente, mirando el
strip-chart. Igual los sentidos (`SENTIDO_X/Y`): dependen de cómo esté
tornillado cada eje. Y GRBL necesita flash + settings en cada Uno nuevo.
