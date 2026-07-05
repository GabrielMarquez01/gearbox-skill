# ⚡ Eficiencia con Agentes — 8 prácticas para no quemar tu presupuesto

> Guía práctica, independiente del Gearbox: **ábrela y úsala.** Ningún dato privado, ningún
> setup previo. Son hábitos que reducen tu gasto (o consumen tus límites más lento) desde hoy.

La mayoría del gasto en agentes **no viene de "usar mucho Claude"** — viene de tres hábitos
que se acumulan sin que los veas:

1. **Sesiones eternas** (dejar una conversación abierta horas, arrastrando todo su historial)
2. **Contexto pesado** (mientras más larga la charla, más caro cada mensaje — aun con caché)
3. **Herramientas que llenan el contexto** (cada resultado de una tool/MCP se queda cargado el resto de la sesión)

Estas 8 prácticas atacan exactamente eso — y al final, un protocolo para **exprimir cada modelo
caro** cuando trabajas con varios en un mismo flujo.

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

## 🔀 El handoff: cómo no desperdiciar un modelo caro

Elegir el modelo correcto es la mitad. La otra mitad es **cómo lo diriges**. Una sesión de un
modelo caro (el "arquitecto") que explora sin rumbo cuesta más que diez sesiones baratas. El
patrón que más ahorra es tratar cada modelo según su rol y hacer el traspaso limpio:

- **El caro piensa, diseña y decide.** No lo pongas a poner ladrillos.
- **El barato ejecuta, edita y documenta.** Es quien construye lo que el caro diseñó.
- **La preparación** (juntar contexto, reducir ambigüedad, volver los hallazgos un plan) es
  trabajo de bajo costo que multiplica el valor de la sesión cara.

### Antes de llamar al modelo caro — prepáralo (5 puntos)
1. **Objetivo** en una frase.
2. **Rutas exactas** que debe mirar (no "busca por ahí").
3. **Qué NO debe hacer** (límites explícitos: no editar, no salirse del alcance).
4. **Hipótesis** a confirmar o refutar (le das dirección, no una hoja en blanco).
5. **Salida estructurada** que esperas (un formato, no prosa libre).

> Un modelo caro con estos 5 puntos entrega en una sesión lo que sin ellos toma tres.

### Durante la sesión cara — mantenlo en carril
- Concede **permisos puntuales**, no permisos amplios de edición.
- Pide **evidencia con archivo + línea**, no afirmaciones.
- **Corta la exploración** en cuanto se salga del objetivo.

### Después — convierte, no ejecutes a ciegas
- Vuelve los hallazgos un **checklist accionable** para el modelo barato.
- **Separa las decisiones de la implementación** — lo que requiere tu OK vs lo mecánico.
- Ejecuta **solo lo aprobado.**

> Este patrón se afina **combinando asistentes**: un modelo prepara el contexto, otro diseña,
> otro ejecuta. La eficiencia real no nace de casarse con un modelo, sino de orquestarlos por rol.

---

Si una de estas prácticas te ahorró tiempo o dinero, **abre un issue contándolo** — la evidencia
real de la comunidad es lo que hace mejor la guía.

---

<div align="center"><sub>⚡ Parte de <b>Gearbox</b> · <a href="README.md">volver al README</a></sub></div>
