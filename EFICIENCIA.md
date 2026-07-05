# ⚡ Eficiencia con Agentes — 8 prácticas para no quemar tu presupuesto

> Guía práctica, independiente del Gearbox: **ábrela y úsala.** Ningún dato privado, ningún
> setup previo. Son hábitos que reducen tu gasto (o consumen tus límites más lento) desde hoy.

La mayoría del gasto en agentes **no viene de "usar mucho Claude"** — viene de tres hábitos
que se acumulan sin que los veas:

1. **Sesiones eternas** (dejar una conversación abierta horas, arrastrando todo su historial)
2. **Contexto pesado** (mientras más larga la charla, más caro cada mensaje — aun con caché)
3. **Herramientas que llenan el contexto** (cada resultado de una tool/MCP se queda cargado el resto de la sesión)

Estas 8 prácticas atacan exactamente eso.

---

## 1. Modelo por tarea — empieza barato, sube solo si te quedas corto

No corras todo en el modelo grande "por si acaso". Un peón hace trabajo de peón.

- **Mecánico** (buscar, renombrar, formatear) → modelo barato / subagentes
- **La mayoría del trabajo** (programar, ejecutar) → modelo intermedio
- **Pensar duro** (arquitectura, decisiones difíciles) → modelo grande, solo ahí

> El Gearbox automatiza esta decisión, pero el principio funciona aunque lo hagas a mano.

## 2. Higiene de sesión — `/compact` y `/clear`

- **`/compact`** a media tarea larga → resume la conversación y libera contexto sin perder el hilo.
- **`/clear`** al cambiar de tema → empiezas limpio, no arrastras el peso de lo anterior.

Regla simple: **al terminar un bloque grande de trabajo, `/compact` (si sigues) o `/clear` (si cambias de tema).**

## 3. Cuida los MCP — cada resultado se queda cargado

Los servidores MCP son potentes, pero **cada resultado que devuelven permanece en tu contexto**
el resto de la sesión, sumando costo mensaje tras mensaje.

- **No conectes servidores que no estás usando** en esta sesión.
- **No dupliques**: dos servidores MCP del mismo servicio conectados = pagas por ambos. Deja uno.
- Después de un bloque pesado de consultas, **`/compact`** para vaciar esos resultados.

## 4. No re-consultes lo que no cambia — cachea en un archivo

Si consultas la misma información estable cada sesión (el esquema de una base de datos, una
config, una tabla de referencia), **guárdala una vez en un archivo local** y léela de ahí.

Consultar un esquema que casi nunca cambia, en cada sesión, desde cero, es puro gasto repetido.

## 5. Queries quirúrgicas — pide solo lo que necesitas

Pedir "dame toda la tabla" trae metadata y filas que no usas — y todo eso ocupa contexto.

- Pide **solo las columnas** que necesitas, con `LIMIT`.
- Para lecturas puntuales que ya sabes formular, una consulta directa suele gastar **una fracción**
  de lo que gasta una herramienta "explorar todo".

## 6. Comando, no memoria — automatiza lo repetitivo

**Todo lo que dependa de que el modelo "se acuerde" de hacerlo, tarde o temprano falla.**

Si algo debe pasar siempre (registrar, formatear, validar), conviértelo en un **script de una
línea o un hook**, no en una instrucción que confías en que el agente recuerde. Menos olvidos,
menos re-trabajos, menos tokens gastados en corregir.

## 7. Delega hacia abajo — lo mecánico a subagentes

Las tareas rutinarias no necesitan tu modelo principal. Mándalas a **subagentes con el modelo
barato**: hacen el trabajo en paralelo y no cargan tu contexto principal con los pasos intermedios.

## 8. Mide tu consumo — no optimizas lo que no ves

Corre **`/usage`** en Claude Code: te muestra de dónde viene tu gasto (sesiones largas, contexto
alto, qué MCP consume más). Es el diagnóstico que convierte "gasto mucho" en "gasto **aquí**, y
esto es lo que ajusto".

---

## ✅ Checklist rápido (pégalo donde lo veas)

- [ ] ¿Estoy en el modelo correcto para ESTA tarea, o en el grande "por si acaso"?
- [ ] ¿Llevo horas en la misma sesión? → `/compact`
- [ ] ¿Cambié de tema? → `/clear`
- [ ] ¿Tengo MCP conectados que no uso, o duplicados? → desconéctalos
- [ ] ¿Estoy re-consultando algo que no cambia? → cáchealo en un archivo
- [ ] ¿Pedí solo lo que necesito, o "toda la tabla"?
- [ ] ¿Esto que hago a mano cada vez debería ser un script?
- [ ] ¿Cuándo corrí `/usage` por última vez?

---

## Por qué esto importa (el costo invisible)

El error más caro y menos obvio: **cambiar de modelo a mitad de sesión reinicia el caché de
prompt.** El descuento por caché (hasta 90%) se pierde, y la siguiente respuesta relee TODO tu
historial a precio completo. Por eso las decisiones de modelo se toman **al inicio de la tarea**,
no a media conversación.

Con suscripción (Pro/Max) esto se traduce en **consumir tus límites más lento**. Con API, es
**dinero directo**. En ambos casos: mismos resultados, menos desperdicio.

---

## 🔭 Hacia dónde va esto

Estas prácticas son **hábitos** — funcionan hoy, a mano. El siguiente paso natural es que dejen de
depender de que te acuerdes: que la herramienta **mida tu gasto real, te muestre dónde ahorraste, y
afine su precisión con tus propios datos** (la filosofía *usar → medir → calibrar*). El Gearbox ya
registra cada decisión con ese fin; hacerlo visible y medible es la dirección de trabajo.

Si una de estas prácticas te ahorró tiempo o dinero, **abre un issue contándolo** — la evidencia
real de la comunidad es lo que decide qué se automatiza siguiente.

---

<div align="center"><sub>⚡ Parte de <b>Gearbox</b> · filosofía SaaS Factory: usar → medir → calibrar · <a href="README.md">volver al README</a></sub></div>
