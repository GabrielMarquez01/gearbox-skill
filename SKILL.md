---
name: gearbox
description: >-
  Selector automático de modelo y esfuerzo por tarea. Se aplica en TODA sesión:
  clasifica cada tarea del usuario en una marcha (G0-G5), recomienda el modelo y
  esfuerzo óptimos con el comando exacto y el costo relativo, delega subtareas
  rutinarias a Haiku, registra cada decisión en bitácora para calibración, y
  vigila mensualmente si hay modelos nuevos. Con varios proveedores (Claude,
  Codex, Gemini) elige también el motor por clase de tarea y por cupo real, y
  exige que el auditor sea de otro proveedor. Triggers: inicio de cualquier tarea,
  gearbox, qué marcha, cambiar modelo, subir marcha, bajar marcha, esfuerzo,
  qué modelo conviene, qué motor, calibrar gearbox, model watch.
---

# Gearbox — Selector Automático de Modelo y Esfuerzo

Actualizado: 2026-11-07 00:29 (America/Mexico_City).

> **Regla de oro:** usar la marcha más baja que entregue resultado confiable,
> y subir solo cuando el riesgo, dinero o complejidad lo justifique.
> Evolución del Gearbox Protocol de OpenGravity: routing de modelos Claude y, desde EV6,
> de motores de varios proveedores (ver §Marcha × motor).

---

## Tabla de Marchas

| Marcha | Tipo de tarea | Modelo · Esfuerzo | Cómo se activa | Economía (precio de lista por token) |
|---|---|---|---|---|
| **G0 Rutina** | búsquedas, lecturas masivas, renombres, formateo, logs | Haiku 5.5 · low (`medium` si la cadena de pasos es larga) | AUTOMÁTICO — delegar a subagente con `model: haiku` | entrada ≈ 1/20 de Sonnet 5.5 (prompts de hasta 100 000 tokens) |
| **G1 Contenido** | copy, redacción, variantes, assets, SEO | Sonnet 5.5 · medium | recomendar `/effort medium` | menos tokens de razonamiento que `high` |
| **G2 Ejecución** (default) | features con contrato claro, UI, DB, fixes, deploys | Sonnet 5.5 · high | `/model sonnet` + `/effort high` (el esfuerzo por defecto depende del modelo y del producto: fíjalo) | base: $2 / $10 por M tokens |
| **G3 Planeación híbrida** | PRPs, features grandes multi-fase | opusplan | recomendar `/model opusplan` (Opus planea → Sonnet ejecuta, cambio automático) | Opus solo al planear |
| **G3.5 Turno profundo** | UNA pregunta difícil aislada | mismo modelo, esfuerzo más alto solo para ese turno | `/effort xhigh` para esa pregunta y volver al nivel anterior | sin cambiar de modelo |
| **G4 Crítico** | seguridad/PII, producción caída, debugging multi-sistema | Opus 5.5 · **xhigh** | recomendar `/model opus` + `/effort xhigh` | ≈2× Sonnet 5.5 por token; se paga solo si evita retrabajo. **Este gate sube, nunca baja** |
| **G5 Arquitectura** | blueprint de ecosistema, infraestructura, decisiones multi-repo, contexto muy grande | **Opus 5.5 · xhigh** por defecto; Fable 5.1 solo cuando Opus 5.5 no alcanza | Opus cubre hoy la mayor parte de esta franja; para Fable 5.1 ver §Candado de costo | Opus 5.5 ≈2× · Fable 5.1 ≈5× Sonnet 5.5; **ambos con ventana de 1M de tokens** |

**Precios de referencia** — tarifa base de la API, USD por millón de tokens (entrada / salida), **consultados el 2026-10-30**
en la [página oficial de precios de Anthropic](https://platform.claude.com/docs/en/about-claude/pricing) y en
[claude.com/pricing](https://claude.com/pricing):

| Modelo | ID de API | Entrada / salida |
|---|---|---|
| Fable 5.1 | `claude-fable-5-1` | $10 / $50 |
| Opus 5.5 | `claude-opus-5-5` | $4 / $20 |
| Sonnet 5.5 | `claude-sonnet-5-5` | $2 / $10 |
| Haiku 5.5 | `claude-haiku-5-5` | $0.10 / $0.50 con prompts de hasta 100 000 tokens · $0.50 / $2.50 por encima |

Los multiplicadores `≈Nx` de esta tabla son **una división** (precio de entrada ÷ $2 de
Sonnet 5.5), no un dato de la página: una brújula por token, no una factura. Las tarifas cambian varias veces
al año — la fuente manda sobre este archivo; vuelve a consultarla antes de decisiones de volumen
(registro fechado en [docs/FUENTES.md](docs/FUENTES.md)).

> **Límite de esta actualización documental:** `prices.json` conserva el catálogo de julio de 2026.
> Su actualización y la de los scripts `.sh` al catálogo Claude 5.x están **pendientes del parche de
> código separado**. Las tablas de este documento no describen los precios que usa hoy el statusline.
> Los ejemplos de pantalla con `≈Nx` ilustran el formato; con el `prices.json` multilínea incluido,
> el lector actual puede omitir el multiplicador (ver §«`≈Nx` — el multiplicador»).

La recomendación oficial de Anthropic para elegir dentro de la familia coincide con la lógica de esta tabla:
empezar por Opus 5.5 para la mayoría de las cargas, y pasar a Fable 5.1 *«para razonamiento exigente y trabajo
agéntico de largo aliento, o cuando tus evaluaciones con Opus 5.5 a mayor esfuerzo no alcanzan»*
(traducción nuestra; [visión general de modelos](https://platform.claude.com/docs/en/about-claude/models/overview)).

> **Antes de aplicar la tabla, verifica qué incluye tu plan.** Si tu suscripción ya cubre el nivel Opus sin costo marginal y Fable se paga aparte por consumo, la comparación deja de ser «2× vs 5×» y pasa a ser **«incluido vs dinero nuevo»**. Eso cambia casi todas las decisiones de la franja alta. Qué modelos y límites incluye cada plan cambia con el tiempo: confírmalo en la página oficial de tu plan.

**Alias o ID fijo.** En Claude Code, los alias (`haiku`, `sonnet`, `opus`, `fable`, `opusplan`) apuntan a la versión
recomendada y se actualizan solos; para el día a día, úsalos. Si necesitas resultados reproducibles (evaluaciones,
pipelines), fija el ID completo (`--model claude-opus-5-5`) o las variables `ANTHROPIC_DEFAULT_*_MODEL`
([configuración de modelos](https://code.claude.com/docs/en/model-config)). **Ojo:** en otros proveedores de nube
los alias pueden resolver a versiones anteriores — comprueba a qué apunta cada uno donde trabajas.

---

## La escalera de esfuerzo (la palanca más subestimada)

Los modelos actuales aceptan un ajuste de **esfuerzo**: cuánto piensan antes de responder. Mueve el
gasto más que cambiar de modelo, y casi nadie lo toca. La escalera tiene cinco peldaños.
Descripciones tomadas de la [doc oficial de esfuerzo](https://platform.claude.com/docs/en/build-with-claude/effort) (consultada el 2026-10-30):

| Esfuerzo | Equivale a | Cuándo | Nota |
|---|---|---|---|
| `low` | "mírame esto rápido" | tareas simples que necesitan la mayor velocidad y el menor costo, como los subagentes | ahorra muchos tokens a cambio de algo de capacidad; en Haiku 5.5, con prompts largos de agente, `low` puede saltarse una búsqueda o una verificación |
| `medium` | "dedícale un rato" | trabajo operativo del día: equilibrio entre velocidad, costo y rendimiento | **es el valor por defecto de Opus 5.5 y de Haiku 5.5** |
| `high` | "piénsalo bien" | razonamiento complejo, código difícil, tareas agénticas | por defecto en Fable 5.1 y Sonnet 5.5 (API); en Claude Code el valor por defecto depende del modelo — compruébalo con `/effort` |
| `xhigh` | "tómate la tarde" | trabajo agéntico y de código largo (la doc habla de tareas de más de 30 minutos) | gasta bastante más tokens que `high`; con `xhigh` o `max`, da margen de salida (`max_tokens`) |
| `max` | "tómate el día" | cuando errar cuesta más que el gasto | en la mayoría de las cargas añade mucho costo por poca mejora y puede sobrepensar — mide antes de fijarlo |

En Claude Code se fija con `/effort <nivel>`, `--effort`, la variable `CLAUDE_CODE_EFFORT_LEVEL` o el ajuste
`effortLevel` (que acepta `low`, `medium`, `high` y `xhigh`; `max` no se acepta en ese ajuste).

**Regla de oro actualizada:** la marcha más baja que entregue resultado confiable — pero medida
contra el modelo que estás usando hoy, no contra el anterior. **Barre `medium → high → xhigh` sobre
tareas reales antes de fijar un default.** Los valores heredados de otra generación casi nunca
transfieren bien (la propia doc lo pide así, en traducción libre: *«corre un barrido de esfuerzo con tus
evaluaciones en vez de arrastrar la configuración de un modelo anterior»*).

**Hipótesis a medir, no un hecho:** en trabajo agéntico largo, subir el esfuerzo puede gastar más por turno y
necesitar menos turnos y menos retrabajo, de modo que el total baje. Depende de la tarea: compruébalo con tu
bitácora (`decisions.jsonl`) antes de generalizarlo.

### Trampas al estrenar un modelo nuevo

Cada generación cambia comportamientos que no vienen en la nota de lanzamiento. Revisa siempre:

- **El esfuerzo por defecto puede bajar de nivel.** Opus 5.5 arranca en `medium`; los Opus anteriores arrancaban en
  `high`. Una petición que no fija `effort` corre **un peldaño más abajo** que antes (doc oficial de esfuerzo).
- **El pensamiento viene encendido y los modos de apagarlo difieren por modelo.** En Opus 5.5 el pensamiento
  adaptativo no se puede apagar (`thinking: {"type": "disabled"}` devuelve error en cualquier esfuerzo); en
  Sonnet 5.5 `disabled` no se acepta y la opción más baja es `between_tools` (en `xhigh`/`max` devuelve error);
  en Haiku 5.5 `disabled` funciona en `high` o menos. Se valida **por petición**, no por conversación.
- **Da margen de salida.** En `high` o más, el pensamiento cuenta dentro de `max_tokens`: si lo ajustas al ras, las
  respuestas se truncan.
- **Revisa tus instrucciones heredadas.** Lo que ayudaba a un modelo anterior («verifica tu trabajo», reglas para
  forzar delegación o concisión) puede duplicar trabajo —y costo— en uno nuevo. Mídelo, no lo asumas.
- **Vigila cuánto delega y cuánto alcance toma.** La tendencia a lanzar subagentes o a ampliar lo pedido cambia
  entre versiones: pon tope y disciplina de alcance por escrito en el prompt del carril.
- **Los límites de uso pueden contarse por modelo o por familia.** Mover tráfico a un modelo nuevo no siempre hereda
  la cuota del anterior. Confírmalo antes de planear volumen.
- **El caché y las tarifas de caché difieren por modelo.** Revisa el mínimo cacheable y el precio de lectura en la
  [doc de precios](https://platform.claude.com/docs/en/about-claude/pricing).

---

## Protocolo del Recomendador (cada tarea del usuario)

```
1. LEER     → clasificar el input contra la tabla (costo ≈ $0, es parte de leer el prompt)
2. COMPARAR → ¿marcha recomendada ≠ configuración actual de la sesión?
   ├─ NO → ejecutar directo, sin ruido
   └─ SÍ → 3. PAUSA: emitir bloque de recomendación ANTES de empezar el trabajo
3. REGISTRAR la decisión en la bitácora — siempre, haya o no cambio de marcha, con el
   comando literal (ver "Bitácora de calibración" abajo):
   ~/.claude/gearbox/log.sh decision <gear_actual> <gear_recomendada> "<task>" [skill] [doc]
```

### Formato del bloque de recomendación (obligatorio, literal)

```
⚙ GEARBOX → conviene subir a Opus / xhigh
   Comando:  /model opus   ·   /effort xhigh
   Razón:    debugging multi-sistema en producción
   Economía: ≈2× Sonnet 5.5 por token pero evita retrabajo; cambiar AHORA (el caché se reinicia al cambiar)
```

Reglas del bloque:
- **Razón**: UNA frase concreta ("planeación estratégica y arquitectura", "copy sin razonamiento profundo")
- **Economía**: costo relativo o ahorro siempre que sea calculable **con las tarifas de la tabla** — si no lo es, dilo; no lo estimes
- Si la recomendación es NO cambiar pero el usuario preguntó, decirlo explícito: "mantener Sonnet/high — la planeación difícil ya pasó"
- Recomendar cambios **al inicio de una tarea**, nunca a la mitad (cambiar modelo reinicia el caché de prompt: la siguiente respuesta relee todo el historial sin el descuento de lectura de caché, que según el modelo va del 90 % al 97.5 %)

### Qué es automático vs qué requiere al humano

| Acción | Quién |
|---|---|
| Delegar subtareas G0 a Haiku (`Agent` con `model: haiku`) | Claude, automático |
| opusplan: Opus al planear → Sonnet al ejecutar | Harness, automático (si `/model opusplan` activo) |
| Cambiar el modelo principal de la sesión | Humano — Claude da el comando exacto |
| Sesión Fable (G5) | Humano — con justificación y, si pagas por consumo, con el bloque de costo explícito |

---

## Candado de costo — el modelo de frontera nunca en frío

> La regla que más dinero ahorra no es técnica, es de gobierno: **nadie —persona o asistente— puede
> proponer el modelo más caro sin poner el precio enfrente.** Una recomendación del modelo de
> frontera sin presupuesto estimado es una recomendación inválida y debe rechazarse.

**Primero corre el nivel Opus.** Solo se escala a Fable si Opus falló **de forma demostrable**, con
evidencia de en qué falló. Escalar por corazonada es gasto injustificado. (Si tu plan incluye Fable sin costo
marginal, el recurso escaso pasa a ser tu **cupo**, no el dinero — el bloque sirve igual: pon el cupo enfrente.)

### Bloque obligatorio antes de convocar Fable

```text
💰 GATE DE COSTO — MODELO DE FRONTERA
Actividad:      qué exactamente, delimitado (no "arquitectura" — qué documento sobre qué)
Por qué éste:   la razón concreta que el nivel Opus no cubre
Presupuesto:    $X – $Y   (rango honesto, nunca una promesa)
TOPE DURO:      $Z — al llegar, la sesión SE DETIENE y reporta; no pide más a media obra
Alternativa:    Opus · xhigh → cubre ~N% de esto
Autorización:   "aprobado hasta $Z"
```

### Topes duros: tú los fijas

No hay un tope «correcto» universal; el tamaño del tope depende de tu bolsillo. Un esquema que funciona es
escalarlo por alcance, con un tope **antes** de empezar y un punto de control a mitad de lo grande:

| Convocatoria | Alcance | Tope duro (ejemplo para que lo sustituyas) |
|---|---|---|
| Turno puntual | UNA pregunta difícil, contexto acotado | un tope bajo |
| Sesión acotada | Un documento / una decisión, fuentes cerradas | un tope medio |
| Trabajo mayor | Multi-repo, multi-hora, varios entregables | un tope alto + checkpoint a mitad |

### Cómo estimar sin calculadora

Estima con tokens de entrada y salida contados para el texto concreto, y con las tarifas
fechadas de [docs/FUENTES.md](docs/FUENTES.md). No conviertas palabras a tokens con una razón fija:
el resultado depende del idioma, el texto y el tokenizador. Incluye el razonamiento facturable
en la salida y declara la incertidumbre antes de pedir autorización.

> ⚠️ **Pensar cuesta 5× más que leer** ($50 contra $10). En Fable 5.1 el razonamiento **no se puede apagar**
> (adaptativo, siempre encendido) y se factura como salida. El costo no escala con cuánto material le des a
> leer, sino con **cuánto tiempo lo dejes deliberando** — por eso las sesiones largas son las que se disparan.

### Planeación previa obligatoria

Todo gate llega **ya planeado**, nunca como sesión abierta sin rumbo:

1. **Entregable declarado** — qué documento o decisión concreta sale. Sin entregable, no hay gate.
2. **Fuentes acotadas** — la lista exacta de repos/documentos, cerrada de antemano. Leer "lo que haga
   falta" es como se revientan los presupuestos.
3. **Criterio de terminado** — cómo se sabrá que ya está, para no deliberar de más.
4. **Qué queda para después** — Fable entrega el plano; la ejecución es trabajo de Opus/Sonnet.

---

## Regla G5 — Fable 5.1 sin humo

Fable 5.1 es para decisiones grandes, ambiguas o de largo contexto. No recomendarlo por prestigio del tema, sino por la forma de la tarea.
Anthropic lo describe como el modelo *«para razonamiento exigente y trabajo agéntico de largo aliento»*; Opus 5.5 también tiene
ventana de 1M de tokens, así que el contexto grande **no** es por sí solo motivo para subir.

Recomendar G5 cuando la tarea pida:
- Blueprint de arquitectura de producto, plataforma o ecosistema completo
- Infraestructura, seguridad, datos, integraciones o tradeoffs difíciles
- Analizar varios repos/documentos juntos sin perder contexto
- Encontrar causa raíz de bugs complejos o problemas de producción
- Convertir una visión ambigua en un plan ejecutable por fases

No recomendar G5 cuando baste con Sonnet/Haiku:
- Copy, SEO, prompts simples o brainstorming ligero
- Fixes pequeños, formateo, renombres, logs o lectura mecánica
- Implementar una tarea ya definida
- Decisiones que se validan mejor con usuarios reales que con más razonamiento

La disponibilidad de Fable en cada plan y su cupo cambian con el tiempo (dato de contexto, no promesa
permanente). No lo uses como argumento de urgencia: confírmalo en la página oficial de tu plan y mantén solo
la regla de buen uso.

Prompt recomendado al sugerir G5:

```text
Estoy usando Fable 5.1. No implementes todavía.
Analiza el contexto completo y dame:
1. arquitectura recomendada,
2. riesgos y tradeoffs,
3. plan por fases,
4. qué debe ejecutar Sonnet,
5. qué puede delegarse a Haiku,
6. cuándo tendría sentido volver a Fable.
```

Reglas de honestidad:
- Los modelos de frontera pueden aplicar salvaguardas más estrictas en ciertas áreas y rechazar una petición; la doc oficial describe cómo manejar los rechazos y reintentar en otro modelo de Claude ([rechazos y fallback](https://platform.claude.com/docs/en/build-with-claude/refusals-and-fallback)).
- No prometer ahorro con Fable: se usa para evitar mala arquitectura o retrabajo caro, no para gastar menos por token.
- Preferir `/model fable` al inicio de la tarea. Evitar cambiar a Fable a mitad de una conversación larga por pérdida de caché.

---

## Marcha × motor — varios proveedores (EV6)

Hasta aquí la palanca era *cuánto piensa* un modelo. Con varios proveedores —Anthropic (Claude), OpenAI (Codex)
y Google (Gemini, por ejemplo dentro de Antigravity)— cada tarea se clasifica en **dos ejes**: la marcha (G0–G5)
y el **motor** que la ejecuta. Esta sección es el **patrón generalizado**; los nombres de modelo de los ejemplos
son ilustrativos y vigentes al 2026-10-30 — sustitúyelos por los de tu propio catálogo.

### Regla 1 — El motor se elige por clase de tarea, no por prestigio

Define pocas clases (por ejemplo **crítica · estándar · ligera**) y, para cada una, una **lista ordenada** de
motores con su esfuerzo. El mejor *para esa clase* va primero — y no siempre es el más caro: una tarea ligera
con el motor de frontera es el mismo derroche que correr todo en Opus.

```text
# Ejemplo de estructura (el orden es tuyo; sale de tu bitácora, no de esta página)
construir:
  critica:  [ proveedor-A:modelo-grande:high , proveedor-B:modelo-grande:high , proveedor-C:modelo-grande:high ]
  estandar: [ proveedor-A:modelo-medio:medium , proveedor-B:modelo-rapido:high ]
  ligera:   [ proveedor-B:modelo-rapido:low , proveedor-A:modelo-chico:low ]
auditar:   # misma idea, con la Regla 3 encima
```

### Regla 2 — Un motor sin cupo se salta solo; el cupo se pregunta, no se lee de una lista

Cada proveedor tiene su propio cupo, y se agota en momentos distintos. Un lanzador con los motores escritos a
mano arranca un motor sin cupo y la tarea muere a los pocos segundos. En su lugar:

1. Cuando un motor responde «sin cupo / límite de uso», se **marca fuera hasta su hora de reinicio** (un archivo de estado con `hasta`).
2. El selector **salta** los motores marcados y toma el siguiente de la lista.
3. Si **no queda ninguno** disponible, el lanzador **no arranca**: sale con un código propio y avisa. Es mejor un aviso claro que un trabajo muerto a medias.
4. La disponibilidad se confirma **preguntándole al motor** (una llamada real, o el estado de uso que el propio CLI expone), nunca leyendo que aparece en una lista de motores instalados: que un nombre figure en el catálogo no demuestra que haya cupo, ni que el motor funcione.

```text
elegir(rol, clase, proveedor_del_constructor = nada):
  para cada motor en lista[rol][clase]:
      si motor.proveedor == proveedor_del_constructor y rol == "auditar":  saltar     # Regla 3
      si motor está marcado fuera (hasta > ahora):                         saltar     # Regla 2
      devolver motor
  salir con código "sin motor"                                                        # no arrancar
```

### Regla 3 — El auditor SIEMPRE es de otro proveedor

*Quien audita no puede ser quien produjo* — y «otro» significa otro **proveedor**, no otro producto:

- Dos productos del mismo laboratorio (por ejemplo, dos modelos de OpenAI) cuentan como **un solo asiento**: sus sesgos están correlacionados.
- Un CLI multi-modelo puede ejecutar **modelos de otro proveedor**. Si una auditoría cruzada de trabajo hecho por Claude se lanza con un modelo Claude *dentro* de otro CLI, es Claude auditando a Claude — y el comando no lo delata. **Fija siempre el modelo del auditor explícitamente y declara su proveedor en el veredicto.** Nunca confíes en el default.
- Para **dinero, legal, fiscal o datos personales**, el segundo veredicto de otro proveedor es obligatorio y además hace falta la aprobación humana (el gate de estas marchas **sube, nunca baja**).
- Si el tercer proveedor está caído, **dilo en el veredicto**: un empate entre dos no se rompe con una moneda al aire.

**Rigor proporcional.** Un auditor que solo sabe pedir más rigor no es un gate, es un freno. Fija un máximo de dos
vueltas de auditoría del encargo; si el resultado sale apretado, sube el rigor — no antes. Un auditor tampoco tiene
que ser caro: auditar es leer y refutar, no crear.

### Reglas operativas que salieron de operar varios motores

- **Un motor pesado por máquina.** Dos auditorías pesadas lanzadas a la vez en el mismo equipo pueden morir por memoria. Pon un «portero» que deje correr una a la vez, o paraleliza en otra máquina.
- **Esfuerzo explícito en el auditor.** Un motor externo que corre con el esfuerzo por defecto del backend puede estar trabajando en su marcha mínima sin que nadie lo sepa. Súbelo por invocación (por ejemplo `codex exec -c model_reasoning_effort=high`) y solo donde la tarea lo merece: el cupo ajeno también es finito.
- **Antes de enviar material sensible a un proveedor, lee qué hace con tus entradas en tu plan** (entrenamiento, revisión humana, retención). «Incluido en mi suscripción» no responde a esa pregunta.
- **La tabla de motores envejece sola.** Los catálogos cambian cada mes: mídelos (el listado de modelos de cada CLI y el changelog oficial) en vez de escribirlos a mano en el lanzador.
- **Cada proveedor tiene sus fricciones.** Observadas en septiembre–octubre de 2026 en nuestras instalaciones —verifícalas contra tu versión—: `codex exec` con un prompt y stdin abierto puede quedarse esperando entrada (el propio `--help` explica que stdin se anexa al prompt: lánzalo con `< /dev/null` desde scripts); y Antigravity en modo headless no puede pedir permisos interactivos, así que o configuras *allow-rules* o le pasas el contenido dentro del prompt en lugar de pedirle que abra archivos.

Más lecciones, con su tropiezo y su regla: [docs/LECCIONES-MULTI-MOTOR-2026-10.md](docs/LECCIONES-MULTI-MOTOR-2026-10.md) ·
arquitectura completa: [docs/GEARBOX-EV6-MULTI-MOTOR.md](docs/GEARBOX-EV6-MULTI-MOTOR.md).

---

## Estado y Bitácora

### Estado visible (statusline V2)

El statusline V2 **deriva la marcha del modelo real** — no del estado guardado.
El modelo real es la fuente de verdad; `state.json` es una intención que se contrasta.
Para Opus conserva G3/G3.5/G4 si ya están guardadas; en otro caso muestra G4. Un modelo
desconocido usa la marcha guardada, o G2 si está en `auto`. La tabla es una recomendación
de uso; el script no cambia el modelo ni implementa un selector entre proveedores.

```
⚙ G5 · Fable 5.1 · high · arquitectura · ≈5x
```

#### `gear=auto` (por defecto)

`reset.sh` escribe `{"gear":"auto",...}`. Con `auto`, el statusline muestra la marcha
derivada del modelo sin ningún aviso. Recomendado: deja `auto` salvo que quieras anclar
una marcha explícita.

#### `GN*` — qué significa el asterisco

El asterisco aparece cuando `state.json` tiene una marcha distinta al modelo real:

```
⚙ G5* · Fable 5.1 · high · ejecución · ≈5x  · state=G2
```

Aquí: el modelo real es Fable 5.1 (→ G5) pero `state.json` dice G2. El `*` lo advierte en azul;
`state=G2` en ámbar dice exactamente qué está almacenado. Para resolverlo:

```bash
~/.claude/gearbox/set.sh G5 arquitectura high   # anclar a G5
~/.claude/gearbox/set.sh auto                   # o volver a auto (sin asterisco nunca)
```

No rompe nada — solo informa. El asterisco nunca bloquea trabajo.

#### `≈Nx` — el multiplicador

Brújula de costo relativo vs Sonnet base, leída de `~/.claude/gearbox/prices.json`.
El `statusline.sh` de `066477c` solo busca `relative`, con la clave del modelo y su valor en la misma
línea. El JSON multilínea incluido no cumple ese formato, por lo que no se muestra `≈Nx` con ese archivo.
El lector independiente del formato está **pendiente del parche de código separado**.
**No es una factura** — usa `/usage` como fuente final. Si el payload de Claude Code trae un costo
real de sesión distinto de cero, el statusline lo muestra como `~$X est.`.

Los dos tramos de Haiku 5.5 están documentados en [docs/FUENTES.md](docs/FUENTES.md), pero el script actual
no lee `context_window.total_input_tokens` ni `relative_long`. La selección de 0.25× para prompts de más
de 100 000 tokens, frente a 0.05× para el tramo corto, está **pendiente del parche de código separado**.

#### El esfuerzo en pantalla — valor recibido, guardado o `high` de respaldo

El statusline prioriza `effort.level` (o `effort` como cadena) del payload y, si falta, usa el valor
de `state.json`. Sin valor guardado o cuando queda `auto`, muestra `high` de respaldo: eso no demuestra
el esfuerzo real del modelo. Mostrar `?` cuando no hay dato está **pendiente del parche de código separado**.

#### Barra de `/usage` — cuánto llevas quemado de tus límites

Desde Claude Code v2.1.80 el payload de statusline trae `rate_limits.{five_hour,seven_day}.used_percentage`
— el mismo dato que `/usage`, sin API externa ni polling. El statusline lo muestra así:

```
⚙ G2 · Sonnet 5.5 · high · ejecución · ≈1x · ▓▓▓░░ 61% 7d · 24% 5h
```

- **7d** (el recurso escaso en plan Pro): barra de 5 bloques `▓`/`░` + porcentaje.
- **5h**: solo el número, sin barra (cambia rápido, la barra marearía).
- Colores: <50% verde · 50–79% ámbar · ≥80% rojo.
- Si el payload no trae `rate_limits` (API, plan free, primer turno de la sesión), no se
  muestra nada — cada ventana puede faltar por separado, nunca se inventa.
- **Persistencia para el guardián opcional:** el `statusline.sh` de `066477c` muestra los porcentajes,
  pero no escribe `~/.claude/gearbox/usage.json`. El [`guardián`](guardian/README.md) lee ese archivo si una
  integración externa lo genera. Persistir porcentajes, renovación y `session_id` con permisos 600 y
  escritura atómica está **pendiente del parche de código separado**; tampoco se ha corregido la
  reutilización de lecturas vencidas.
- Pieza gearbox-nativa: si 7d≥80% y la marcha activa es G4/G5, aparece un hint ámbar:
  `⚠ 7d al NN% en marcha cara — considera bajar`. El `≈Nx` dice qué tan rápido quemas;
  la barra dice cuánto llevas quemado; el hint conecta ambos con la decisión de marcha.

### Actualizar la marcha con `set.sh`

```bash
~/.claude/gearbox/set.sh G5 arquitectura high   # fijar a G5
~/.claude/gearbox/set.sh G2 ejecución high      # volver a Sonnet/ejecución
~/.claude/gearbox/set.sh auto                   # modo auto (recomendado al cerrar sesión especial)
```

Marchas válidas: `auto G0 G1 G2 G3 G3.5 G4 G5`.
El segundo y tercer argumento son opcionales (defaults: la tarea de la marcha y `effort=high`).
Cambiar el default a `effort=auto` está **pendiente del parche de código separado**.

### Bitácora de calibración: dos ríos separados

`log.sh` escribe en dos archivos distintos según el tipo de dato — un evento de `set`/`reset`
no tiene valor de calibración (solo dice "abrí sesión" o "cambié estado"); una decisión
clasificada sí lo tiene. Mezclarlos hacía la Calibración Fase 2 imposible de analizar.

**`events.jsonl`** — automático, `set.sh`/`reset.sh` escriben aquí en cada llamada:

```json
{"ts":"...","gear":"G5","task":"arquitectura","effort":"high","action":"set","model":"Fable 5.1"}
```

**`decisions.jsonl`** — el dato que calibra. Se escribe con el comando literal del paso 3
del protocolo, SIEMPRE que se clasifique una tarea (haya o no cambio de marcha):

```bash
~/.claude/gearbox/log.sh decision <gear_actual> <gear_recomendada> "<task>" [skill] [doc]
```

Ejemplo ilustrativo:

```bash
~/.claude/gearbox/log.sh decision G2 G2 "fix de bug en checkout" supabase
```

Esquema ilustrativo (una línea JSONL; el modelo depende del valor recibido o guardado):

```json
{"ts":"...","model":"Sonnet 5.5","gear_actual":"G2","gear_recomendada":"G2",
 "task":"fix de bug en checkout","skill":"supabase","accion":"ejecutar",
 "doc":"","retrabajo":false}
```

`accion` se auto-deriva (`ejecutar` si `gear_actual`==`gear_recomendada`, si no
`recomendar-cambio`) o se pasa explícito como 6º argumento — usar `delegar-haiku` cuando
la tarea se delega a un subagente Haiku (G0), para que la delegación deje rastro:

```bash
~/.claude/gearbox/log.sh decision G2 G0 "buscar todas las referencias a X" "" "" delegar-haiku
```

**Retrabajo** — LA señal de marcha insuficiente. Si una tarea tuvo que rehacerse, registrar
una línea nueva (JSONL es append-only, no se edita la anterior):

```bash
~/.claude/gearbox/log.sh retrabajo "<task>"
```

**Modelo:** ambos comandos registran el modelo si está disponible — vía `GEARBOX_MODEL`
(variable de entorno) o como último argumento en modo evento
(`set.sh <gear> [task] [effort] [model]`). Si ninguno de los dos llega, `log.sh decision`
cae al último `model` conocido en `state.json` (persistido ahí por `set.sh` desde 2026-07-13,
fix GEARBOX-HIGIENE). Nunca se inventa: si tampoco hay dato en `state.json`, el campo queda
vacío — no se adivina el modelo.

**Skill:** `log.sh decision` valida el 4º campo contra los skills instalados en
`~/.claude/skills/` (más un allowlist corto de skills globales de Claude Code sin carpeta
local: `deep-research`, `security-review`, etc.) o el literal `ninguno`. Un valor vacío o
que no matchea ninguno de los dos se normaliza a `ninguno` — evita que valores fragmentados
(ej. `security` en vez de `security-review`) ensucien la Calibración Fase 2.

El historial previo a este esquema vive en `~/.claude/gearbox/log.jsonl.v1` (archivado,
nunca borrado — 3 esquemas incompatibles convivían ahí; ver auditoría 2026-07-06).
El análisis de `decisions.jsonl` alimenta la Calibración Fase 2.

---

## Calibración Fase 2 (semi-automática, gate humano)

Umbral mínimo utilizable: **≥10 decisiones por skill** en `decisions.jsonl` antes de proponer
un frontmatter `effort:` — menos que eso no es evidencia, es ruido.

Cuando un skill alcance el umbral:
1. Analizar: en qué marcha corrió y si hubo `retrabajo:true`
2. Proponer al usuario la tabla `skill → effort` para los frontmatter faltantes, CON evidencia
3. Solo con su OK, editar el frontmatter `effort:` de cada skill

Skills ya calibradas por naturaleza obvia (no requieren datos):
`playwright-cli: low` · `primer: low` · `update-sf: low` · `image-generation: low` ·
`prp: high` · `bucle-agentico: high` · `supabase: high` · `compliance: high` · `guardian: high`

---

## Model Watch (revisión mensual)

### Registro — 2026-10-30 · familia Claude 5.x

Fuente: [visión general de modelos](https://platform.claude.com/docs/en/about-claude/models/overview),
[precios](https://platform.claude.com/docs/en/about-claude/pricing) y
[esfuerzo](https://platform.claude.com/docs/en/build-with-claude/effort), consultadas ese día (detalle en [docs/FUENTES.md](docs/FUENTES.md)).

**Qué hay hoy:** Fable 5.1 (`claude-fable-5-1`), Opus 5.5 (`claude-opus-5-5`), Sonnet 5.5 (`claude-sonnet-5-5`) y
Haiku 5.5 (`claude-haiku-5-5`). Los cuatro tienen ventana de 1M de tokens y salida máxima de 128K; el pensamiento es
adaptativo en todos y, en Fable 5.1 y Opus 5.5, no se puede apagar.

**Qué cambió frente a la revisión anterior:**
(1) **Opus 5.5 baja a $4 / $20** (el Opus anterior costaba $5 / $25) y su esfuerzo por defecto es **`medium`**, no `high`;
(2) **Haiku 5.5 se cobra por tramo de prompt**: $0.10 / $0.50 hasta 100 000 tokens y $0.50 / $2.50 por encima;
(3) el precio de **Sonnet 5 de lanzamiento ($2 / $10) pasó a ser el estándar** y el aumento anunciado no ocurrirá; Sonnet 5.5 cuesta lo mismo;
(4) **Fable 5.1** (lanzado el 2026-09-01) mantiene $10 / $50 y baja la lectura de caché a una cuarta parte del costo anterior de Fable;
(5) en Claude Code, los alias `opus`, `sonnet`, `haiku` y `fable` resuelven hoy a Opus 5.5, Sonnet 5.5, Haiku 5.5 y Fable 5.1 sobre la API de Anthropic; **en otros proveedores de nube pueden resolver a versiones anteriores**.

**Qué NO cambió:** la lógica de la tabla (marcha más baja que entregue resultado confiable; los gates de seguridad, PII y dinero suben, nunca bajan) y la recomendación de empezar por Opus antes de convocar a Fable.

**Decisión de flota:** las tareas operativas bajan a `medium`; el código y el trabajo agéntico largo se prueban en `xhigh` con un barrido sobre tareas reales; el ahorro sale de la rutina, nunca de los candados.

La fecha de última revisión vive en `~/.claude/gearbox/watch.json` (`{"last_watch":"YYYY-MM-DD"}`)
— un archivo propio que ningún `reset.sh` toca (a diferencia de `state.json`, que se reescribe
completo en cada SessionStart). Si tu proyecto ya tiene un hook `SessionStart` propio (no lo
instala `install.sh`; es infraestructura opcional que cada quien conecta a su gusto), puede leer
este archivo y agregar un aviso pasivo al contexto (`⚙ Model Watch pendiente`) si pasaron más de
30 días desde la última revisión, o si nunca se ha registrado una. Sin ese hook, revisar
`watch.json` a mano una vez al mes cumple lo mismo.

Cuando el aviso aparezca (o una vez al mes por iniciativa propia):
1. Consultar https://platform.claude.com/docs/en/about-claude/models/overview (y, si usas otros motores, el listado de modelos de cada CLI y su changelog oficial)
2. Si hay modelo de categoría nueva (no solo versión — los alias cubren versiones):

```
⚙ GEARBOX → modelo nuevo detectado: [nombre]
   Precio: $X/$Y · Capacidades: [resumen 1 línea]
   Propuesta: agregarlo como marcha GX para [tipo de tarea]
   ¿Actualizo la tabla? [requiere OK del usuario]
```

3. Solo con OK, actualizar la Tabla de Marchas de este archivo y, en un cambio de código autorizado por separado, `prices.json` (con la fecha de consulta). El `install.sh` actual instala `prices.json` solo si no existe; conserva cualquier copia existente. No implementa `PRICES_ANTERIORES` ni `prices.json.nuevo`: la migración por huellas y la entrega de una copia nueva a quien personalizó sus precios están **pendientes del parche de código separado**.
4. Actualizar `~/.claude/gearbox/watch.json` con la fecha de hoy — haya o no modelo nuevo,
   la revisión en sí misma resetea el conteo de 30 días.

---

## Errores a evitar (heredados del Gearbox Protocol de OpenGravity)

- Usar marcha alta para decidir cosas que se validan barato (10 DMs > multi-LLM)
- Cambiar de modelo a mitad de una tarea larga (caché perdido > ahorro)
- Subir a Fable sin justificar por qué Opus no alcanza (y sin presupuesto, si pagas por consumo)
- Clasificar por la IMPORTANCIA del tema en vez de por la TAREA que viene
  (iterar preguntas sobre un plan ya hecho = ejecución ligera, aunque el tema sea estratégico)
- Usar un alias sin saber a qué versión resuelve donde trabajas, o fijar un ID cuando lo que querías era heredar versiones nuevas
- Fijar un esfuerzo heredado de otra generación sin barrerlo sobre tareas reales
- Lanzar un motor sin cupo y esperar a que «ya veremos»: el selector lo salta, el lanzador avisa
- Dar por «auditoría cruzada» una revisión que, sin que el comando lo diga, corrió en el mismo proveedor que produjo
