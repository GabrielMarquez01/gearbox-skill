<div align="center">

![Gearbox](assets/banner.svg)

**Deja de pagar precio de Opus por tareas de Haiku.**
Gearbox es un **recomendador de modelo y esfuerzo para Claude Code**: clasifica cada tarea,
te dice la marcha óptima con el comando exacto, delega lo rutinario automáticamente cuando puede,
y muestra la marcha activa en azul bajo tu terminal.

[![Instalar](https://img.shields.io/badge/⚙_INSTALAR-1_línea,_2_minutos-1f6feb?style=for-the-badge)](#-instalación)
[![Licencia MIT](https://img.shields.io/badge/Licencia-MIT-green?style=for-the-badge)](LICENSE)
[![Claude Code](https://img.shields.io/badge/Claude_Code-v2.1.170+-8b5cf6?style=for-the-badge)](https://code.claude.com)

*Incluye soporte para **Claude Fable 5** (marcha G5) — el modelo más capaz de Anthropic.*

</div>

---

## 🎬 Así se ve

![Demo](assets/demo.svg)

Escribes tu tarea → Gearbox la clasifica → si conviene otra marcha, **pausa y te lo dice antes de gastar**: comando exacto, razón en una frase, y cuánto ahorras (o cuánto cuesta no cambiar). La línea azul de abajo siempre muestra tu marcha, modelo real y esfuerzo.

## 🧭 No es otro statusline

La mayoría de herramientas para Claude Code te dicen **cuánto gastaste**. Gearbox intenta ayudarte a decidir **antes de gastar**.

| Herramienta | Punto fuerte | Modelos nuevos | Qué le falta frente a Gearbox |
|---|---|---|---|
| **ccusage statusline** | Costo real, gasto diario, burn rate, bloques de uso | Depende de su tabla de pricing y updates | Observa consumo; no recomienda cambiar de marcha por tarea |
| **Claude Powerline** | Statusline pulido, temas, costo, soporte de pricing para `claude-fable-5` | Sí incluye Fable 5 en pricing | Muestra estado; no clasifica intención ni propone `/model`/`/effort` |
| **CCometixLine** | Statusline robusto en Rust, TUI, reconocimiento flexible de modelos | Reconoce nuevas versiones por patrón, como Sonnet 5 | Buen display; no es un protocolo de decisión de costo/calidad |
| **claude-code-statusline** | Simple, directo, muestra modelo/tokens/costo | Más centrado en Sonnet 4.5/Opus/Haiku | No cubre Fable 5 ni routing por complejidad |
| **Claude Code nativo** | Aliases oficiales (`haiku`, `sonnet`, `opus`, `fable`, `best`, `opusplan`) | Sí, vía aliases oficiales | Te da las piezas; Gearbox pone la regla de decisión |

**Posicionamiento:** ccusage/Powerline/CCometixLine son tableros. Gearbox es el copiloto que te dice cuándo bajar, mantener o subir de modelo.

### Qué sí hace

- Recomienda la marcha correcta antes de empezar una tarea.
- Da el comando exacto: `/model opusplan`, `/model opus`, `/effort medium`, `claude --model fable`, etc.
- Explica la razón en una frase y el impacto económico estimado.
- Mantiene una bitácora para calibrar después con evidencia.

### Qué no promete

- No cambia el modelo principal sin el humano: Claude Code no expone un cambio automático universal para eso.
- No compite con dashboards de gasto: puede convivir con `ccusage` o Powerline.
- No activa Fable 5 solo: siempre requiere gate de costo explícito.

## ⚙ Instalación

**Opción A — 1 línea (recomendada):**

```bash
curl -fsSL https://raw.githubusercontent.com/GabrielMarquez01/gearbox-skill/master/install.sh | bash
```

**Opción B — manual:** clona el repo y corre `bash install.sh`, o copia los archivos según [instalación manual](#-instalación-manual).

Reinicia Claude Code y listo. El instalador hace **backup** de tu `settings.json` antes de tocarlo.

> Requisitos: Claude Code v2.1.170+ (`claude update`) · bash · python3 (para el merge seguro de settings). Sin más dependencias — los scripts son bash+sed puros, no necesitas jq.

## 🏎️ Las Marchas

> **Regla de oro:** usa la marcha más baja que entregue resultado confiable, y sube solo cuando el riesgo, dinero o complejidad lo justifique.

| Marcha | Para qué | Modelo · Esfuerzo | Cómo se activa | Economía |
|---|---|---|---|---|
| **G0 Rutina** | búsquedas, logs, formateo | Haiku · low | 🤖 automático (subagentes) | **−67%** vs Sonnet |
| **G1 Contenido** | copy, redacción, SEO | Sonnet · medium | `/effort medium` | −30-50% razonamiento |
| **G2 Ejecución** | features, UI, fixes | Sonnet · high | *default* | base |
| **G3 Planeación** | PRPs, features grandes | **opusplan** | `/model opusplan` → 🤖 Opus planea, Sonnet ejecuta, cambia solo | Opus solo al planear |
| **G3.5 Turno profundo** | 1 pregunta difícil | ultrathink | palabra `ultrathink` en el prompt | $0 de cambio |
| **G4 Crítico** | seguridad, producción caída | Opus · high | `/model opus` · `/fast` para latencia baja | ≈1.7× Sonnet estándar, se paga solo |
| **G5 Arquitectura** | ecosistema completo, infraestructura, decisiones multi-repo | **Fable 5** · high | `/model fable` o `claude --model fable` + gate de costo | 2× Opus |

Precios de referencia (jul 2026, por millón de tokens in/out): Haiku $1/$5 · Sonnet $3/$15 estándar (Sonnet 5 tiene intro $2/$10 hasta 2026-08-31 donde aplique) · Opus $5/$25 · **Fable 5 $10/$50**.
También existe el alias `best`: usa Fable si tu organización tiene acceso, si no el mejor Opus disponible. `/fast` activa el modo rápido de Opus (más velocidad de salida, mismo modelo) — útil en G4 cuando la latencia importa tanto como la calidad.

## 🎯 Qué significa `G5*` (el asterisco)

A partir de la **V2** el statusline muestra la marcha **derivada del modelo real**, no la guardada. El asterisco aparece cuando las dos difieren:

```
⚙ G5* · Fable 5 · high · ejecución · ≈5x  · state=G2
```

| Parte | Qué significa |
|---|---|
| `G5*` | El modelo real (Fable) corresponde a G5; el asterisco dice "pero state.json guarda otra cosa" |
| `≈5x` | Multiplicador vs Sonnet base — brújula de costo, **no factura** |
| `state=G2` | Ámbar: lo que está almacenado en state.json |

**Para resolver el asterisco:**

```bash
~/.claude/gearbox/set.sh G5 arquitectura high   # anclar a G5
~/.claude/gearbox/set.sh auto                   # o volver a auto (nunca habrá asterisco)
```

> El asterisco nunca bloquea trabajo. Es solo información.

## ⚙ `gear=auto` — el modo recomendado

`reset.sh` escribe `{"gear":"auto"}` al inicio de cada sesión. Con `auto`:
- El statusline muestra la marcha derivada del modelo real, sin asterisco nunca.
- Si arrancas con Fable → muestra G5. Si usas Sonnet → muestra G2. Automático.
- Solo usa `set.sh` cuando quieras **anclar** una marcha específica (y limpiarla con `set.sh auto` al terminar).

## 🕹 Usar `set.sh`

```bash
# Fijar marcha (con task y effort opcionales)
~/.claude/gearbox/set.sh G5 arquitectura high
~/.claude/gearbox/set.sh G2 ejecución high
~/.claude/gearbox/set.sh G0 rutina low

# Volver a modo auto
~/.claude/gearbox/set.sh auto

# Marchas válidas: auto G0 G1 G2 G3 G3.5 G4 G5
```

`set.sh` escribe `state.json`, llama a `log.sh` (bitácora automática) y confirma con un mensaje.

## 💲 El multiplicador `≈Nx` — brújula, no factura

`prices.json` guarda multiplicadores relativos vs Sonnet base. El statusline los muestra como orientación:

| Modelo | Multiplicador |
|---|---|
| Haiku | ≈0.5x |
| Sonnet | ≈1x (base) |
| Opus | ≈2.5x |
| Fable | ≈5x |

**Fuente final siempre: `/usage`** — el multiplicador es aproximado y no reemplaza la factura real.
Si el payload de Claude Code trae un costo real de sesión (`cost.total_cost_usd`), el statusline lo muestra como `~$X est.`

Para actualizar precios: editar `~/.claude/gearbox/prices.json` (no se sobrescribe en reinstalaciones).

## 📊 La barra de `/usage` — cuánto llevas quemado

Desde Claude Code v2.1.80 el payload de statusline incluye `rate_limits.{five_hour,seven_day}.used_percentage` — el mismo dato que muestra `/usage`, sin API externa ni polling. El statusline la agrega después del multiplicador:

```
⚙ G2 · Sonnet 5 · high · ejecución · ≈1x · ▓▓▓░░ 61% 7d · 24% 5h
```

- **7d** (el recurso escaso en plan Pro): barra de 5 bloques `▓`/`░` + porcentaje.
- **5h**: solo el número — cambia rápido, una barra ahí marearía más que ayudar.
- Colores: <50% verde · 50–79% ámbar · ≥80% rojo.
- Si tu plan no expone `rate_limits` (API, free, o el primer turno de la sesión), la sección
  simplemente no aparece — cada ventana puede faltar por separado, Gearbox nunca inventa un número.
- **La pieza gearbox-nativa:** si 7d≥80% y la marcha activa es G4 o G5, aparece un hint ámbar —
  `⚠ 7d al NN% en marcha cara — considera bajar`. El `≈Nx` dice qué tan rápido quemas; la barra
  dice cuánto llevas quemado; el hint conecta ambos con la decisión de marcha.

## 🧠 Cómo funciona

```
Tu prompt
   ↓
1. LEER     — Gearbox clasifica la tarea contra la tabla (costo ≈ $0, es parte de leer tu prompt)
2. COMPARAR — ¿marcha recomendada ≠ configuración actual?
   ├─ NO → trabaja directo, sin ruido
   └─ SÍ → 3. PAUSA + bloque ⚙ GEARBOX antes de gastar un token de más
   ↓
4. BITÁCORA — cada decisión queda en ~/.claude/gearbox/decisions.jsonl (separada de
   events.jsonl, que solo registra cambios de estado sin valor de calibración)
   → con ≥10 decisiones por skill, Gearbox propone calibrar su esfuerzo CON EVIDENCIA
```

**Los 3 errores de dinero que ataca:**
1. 💸 Correr todo en el modelo grande "por si acaso" → 40-400% extra en tareas que Sonnet/Haiku resuelven igual
2. 🔄 Correr lo difícil en el modelo barato → retrabajos que cuestan más que el ahorro
3. 👻 El invisible: cambiar de modelo **a mitad de sesión** reinicia el caché de prompt (descuento del 90% perdido — la siguiente respuesta relee TODO tu historial a precio completo). Gearbox recomienda en el momento correcto: al inicio de la tarea.

## 💰 Números reales (datos de una sesión real, 2026-07-04)

> Para el usuario técnico y no técnico: esto es lo que pasa cuando divides los roles bien.

Una sesión de trabajo intenso (~6 horas, 15 deploys, 30 archivos editados, auditoría de seguridad completa):

| Escenario | Costo estimado | Comparado con todo en Fable |
|---|---|---|
| Todo en **Fable 5** | $25–50 | base (el más caro) |
| **Fable planea + Opus ejecuta** (lo que ocurrió sin Gearbox activo) | ~$12–25 | **−50%** |
| **Fable planea + Sonnet ejecuta** (lo que recomienda Gearbox) | ~$7–15 | **−70%** |
| Rutina delegada a **Haiku** | ~$2.50–5 | **−90%** |

**En cristiano:** si usas Fable para pensar el problema difícil y Sonnet para construir la solución, pagas 3 veces menos que si dejas a Fable hacer todo. Y si además delegas las búsquedas y formateos a Haiku, llegas a 10× más barato.

**Lo que reveló la sesión:** el Gearbox detectó que la sesión corría en Opus cuando debía correr en Sonnet — diferencia invisible, pero ~20% de sobre-pago. Ese hallazgo originó la detección de desincronización (`⚠ desync`) que ahora incluye el statusline.

> Margen de error: ±20% (los tokens exactos solo los ve Anthropic en `/usage`). Los ratios son fijos — vienen de precios públicos, no de estimaciones.

**Para usuarios con plan Pro/Max:** el ahorro se traduce en *consumir tus límites más lento* — Fable consume ~2× más rápido que Opus, y Haiku consume ~5× menos que Sonnet. Mismo trabajo, más tiempo antes de toparte con el techo.

## ⚡ Guía de eficiencia (úsala aunque no instales nada)

El Gearbox elige el modelo por ti, pero **la mitad del ahorro son hábitos** — y esos funcionan con
o sin la skill. Reunimos las 8 prácticas que más bajan el gasto (sesiones, contexto, MCP, caché)
en una guía práctica de "ábrela y úsala":

**→ [EFICIENCIA.md](EFICIENCIA.md)** — 8 prácticas + checklist rápido, sin setup, sin dependencias.

Un adelanto de las que más pesan:
- **Higiene de sesión** — `/compact` a media tarea larga, `/clear` al cambiar de tema
- **Cuida los MCP** — cada resultado se queda en contexto; desconecta lo que no usas, no dupliques
- **No re-consultes lo que no cambia** — cachea el esquema/config en un archivo, no en cada sesión
- **Mide** — corre `/usage` para ver de dónde viene tu gasto antes de optimizar

## 🔮 Fable 5 — la marcha G5

[Claude Fable 5](https://www.anthropic.com/news/claude-fable-5-mythos-5) es el modelo más capaz que Anthropic ha liberado (junio 2026, re-disponible desde julio tras los controles de exportación). Contexto de **1M tokens**, salida de 128k, hecho para tareas "más grandes que una sentada": arquitectura de sistemas, investigaciones de causa raíz, sesiones autónomas largas.

### Ventana Fable 5: úsalo con intención

Anthropic anunció que Fable 5 está disponible globalmente desde el **2026-07-01** en Claude Platform, Claude.ai, Claude Code y Claude Cowork. Para Pro, Max, Team y algunos planes Enterprise, estuvo incluido hasta **50% de los límites semanales hasta el 2026-07-07**; esa ventana ya cerró — desde entonces se usa vía créditos de uso si tu plan los tiene habilitados. Fuente: [Redeploying Fable 5](https://www.anthropic.com/news/redeploying-fable-5).

Eso no significa "úsalo para todo". Significa: gastarlo en decisiones que cambian la dirección del proyecto, tengas o no acceso incluido.

**Úsalo para:**
- Blueprint de arquitectura de un producto o ecosistema completo
- Infraestructura, seguridad, datos, integraciones y tradeoffs difíciles
- Analizar varios repos/documentos juntos sin perder contexto
- Encontrar causa raíz de bugs complejos o problemas de producción
- Convertir una visión ambigua en plan de ejecución por fases

**No lo uses para:**
- Copy, SEO, prompts simples o brainstorming ligero
- Fixes pequeños, formateo, renombres, logs o lectura mecánica
- Implementar tareas ya definidas que Sonnet puede ejecutar bien
- Preguntas que se validan mejor con usuarios reales que con más razonamiento

Prompt recomendado para G5:

```text
Estoy usando Fable 5. No implementes todavía.
Analiza el contexto completo y dame:
1. arquitectura recomendada,
2. riesgos y tradeoffs,
3. plan por fases,
4. qué debe ejecutar Sonnet,
5. qué puede delegarse a Haiku,
6. cuándo tendría sentido volver a Fable.
```

Gearbox lo trata como marcha especial:
- **Nunca se activa solo** — siempre con gate de costo explícito (es 2× Opus: $10/$50)
- Se usa idealmente al inicio de una sesión dedicada (`/model fable` o `claude --model fable`), no a mitad de una tarea larga
- El punto dulce: cargar tu ecosistema, restricciones y objetivos en el contexto de 1M y pedirle el blueprint completo
- Si el tema toca ciberseguridad o biología, puede haber rechazos o fallback por clasificadores de seguridad; no es una falla de Gearbox

También existe el alias `best`: usa Fable si tu organización tiene acceso, si no el mejor Opus.

### ¿Y Claude Mythos 5?

Mythos 5 es **el mismo modelo que Fable 5 pero con salvaguardas levantadas** en ciertas áreas (ciberseguridad ofensiva, biología). **No es de acceso público y no tiene auto-enrolamiento**:

- Restringido a **partners de [Project Glasswing](https://www.anthropic.com/project/glasswing)** (equipos de ciberdefensa e infraestructura crítica) e investigadores de biología seleccionados
- Requiere acuerdos formales bajo ASL-4, vetting de personal, auditoría continua y retención obligatoria de 30 días del tráfico
- El camino: contactar a tu account team de Anthropic, AWS o Google Cloud y pasar la aprobación

**Para el 99.9% de desarrolladores: Fable 5 ES el techo.** Si Fable rechaza una solicitud legítima de seguridad (sus clasificadores re-rutean a Opus 4.8 automáticamente), esa es la señal de que tu caso de uso requeriría el programa Glasswing.

## ❓ FAQ

<details><summary><b>¿Cambia el modelo de mi sesión automáticamente?</b></summary>

Lo que puede ser automático, lo es: las subtareas rutinarias van a Haiku vía subagentes sin preguntarte, y `opusplan` cambia solo entre Opus (planear) y Sonnet (ejecutar). El modelo **principal** de la sesión solo puede cambiarlo el humano — no existe API para que Claude se cambie a sí mismo — por eso Gearbox te da el comando exacto listo para copiar.
</details>

<details><summary><b>¿Gearbox es oficial de Anthropic?</b></summary>

No. Gearbox es un proyecto open-source independiente de OpenGravity/Gabriel Marquez. Usa piezas oficiales de Claude Code como `statusLine`, aliases de modelo, skills, subagentes y comandos `/model`/`/effort`, pero no está afiliado ni respaldado por Anthropic.
</details>

<details><summary><b>¿Es seguro instalarlo con curl | bash?</b></summary>

El instalador copia 7 archivos a `~/.claude` (`SKILL.md`, `README.md`, `statusline.sh`, `reset.sh`, `set.sh`, `log.sh` y `prices.json`, este último solo si no existe ya uno), crea backup de `settings.json`, registra `statusLine` y agrega una directiva a `CLAUDE.md`. Aun así, si prefieres revisar antes de ejecutar, clona el repo y corre `bash install.sh` manualmente.
</details>

<details><summary><b>¿La ventana de Fable 5 hasta el 2026-07-07 significó uso gratis ilimitado?</b></summary>

No, y esa ventana ya cerró. Anthropic anunció inclusión hasta 50% de límites semanales para Pro, Max, Team y algunos Enterprise hasta el 2026-07-07. No fue ilimitado, dependía del plan, y desde que cerró se usa vía usage credits si tu cuenta los tiene habilitados. Gearbox la mencionó como oportunidad temporal, nunca como promesa permanente.
</details>

<details><summary><b>¿Por qué no usar Fable 5 para todo?</b></summary>

Porque Fable 5 cuesta más, consume límites más rápido y su valor real está en decisiones difíciles: arquitectura, infraestructura, raíz de bugs complejos y contexto grande. Para implementación normal, Sonnet suele ser mejor equilibrio. Para rutina, Haiku o subagentes baratos son suficientes.
</details>

<details><summary><b>¿Qué pasa si Fable 5 rechaza una tarea?</b></summary>

Fable 5 tiene clasificadores de seguridad más estrictos, especialmente en áreas como ciberseguridad o biología. Puede rechazar o hacer fallback a otro modelo. Eso no rompe Gearbox: simplemente significa que conviene seguir con Opus/Sonnet o reformular la tarea de forma defensiva y legítima.
</details>

<details><summary><b>¿Funciona con plan Pro/Max o solo con API?</b></summary>

Ambos. Con suscripción, el "ahorro" se traduce en consumir tus límites más lento (Fable consume ~2× más rápido que Opus; Haiku muchísimo menos que Sonnet). Con API, es dinero directo.
</details>

<details><summary><b>¿Cuánto ahorra realmente?</b></summary>

Depende de tu mezcla de tareas. Referencia: si hoy corres todo en Opus y tu trabajo es 70% ejecución/rutina, mover eso a Sonnet/Haiku ahorra ~40-60% del gasto total. El error inverso (todo en barato) cuesta en retrabajos — por eso Gearbox también recomienda **subir**.
</details>

<details><summary><b>¿Qué es opusplan?</b></summary>

Un alias oficial de Claude Code: usa Opus durante el modo plan (razonamiento/arquitectura) y cambia automáticamente a Sonnet al ejecutar. El arquitecto diseña, los albañiles construyen — y no pagas al arquitecto por poner ladrillos. Actívalo con `/model opusplan`.
</details>

<details><summary><b>¿Qué es ultrathink?</b></summary>

Una palabra clave: escríbela en cualquier prompt y ese turno razona más profundo, sin cambiar modelo ni configuración. Perfecta para UNA pregunta difícil aislada — la marcha G3.5.
</details>

<details><summary><b>¿No tengo acceso a Fable 5, se rompe algo?</b></summary>

No. G5 es una recomendación con comando — si no tienes acceso, el picker no lo mostrará y usas Opus (G4). El alias `best` resuelve esto solo.
</details>

<details><summary><b>El statusline azul no aparece</b></summary>

1. Reinicia Claude Code (la configuración carga al inicio). 2. Verifica que `~/.claude/settings.json` tenga el bloque `statusLine`. 3. Prueba el script a mano: `echo '{"model":{"display_name":"Test"}}' | bash ~/.claude/gearbox/statusline.sh` — debe imprimir la línea azul.
</details>

<details><summary><b>¿El instalador rompe mi settings.json?</b></summary>

No: hace **merge** (preserva tus hooks, permisos y preferencias) y guarda backup en `settings.json.backup-gearbox`. Si ya tenías `model` configurado, lo respeta.
</details>

<details><summary><b>¿Windows / WSL / macOS / Linux?</b></summary>

WSL, macOS y Linux: soportado (bash + sed + python3, presentes por defecto). Windows nativo (PowerShell): los scripts requieren Git Bash o WSL.
</details>

<details><summary><b>¿Y cuando salgan modelos nuevos?</b></summary>

Dos niveles: (1) versiones nuevas — Gearbox usa **alias** (`sonnet`, `opus`, `haiku`, `fable`), que Anthropic apunta siempre a la última versión, cero mantenimiento; (2) categorías nuevas — el protocolo incluye un *model watch* mensual: Gearbox consulta la página oficial de modelos y te propone integrar lo nuevo a la tabla, con tu aprobación.
</details>

<details><summary><b>¿Cómo se calibra con mis datos?</b></summary>

Cada clasificación se registra en `~/.claude/gearbox/decisions.jsonl` (con el comando `log.sh decision`, separado de `events.jsonl` que solo registra cambios de estado). Con ≥10 decisiones acumuladas para un skill, Gearbox propone su nivel de esfuerzo (frontmatter `effort:`) con la evidencia de cada una. Nada cambia sin tu OK.
</details>

<details><summary><b>¿Cómo desinstalo?</b></summary>

```bash
rm -rf ~/.claude/gearbox ~/.claude/skills/gearbox
mv ~/.claude/settings.json.backup-gearbox ~/.claude/settings.json
# y borra la sección "## Gearbox" de ~/.claude/CLAUDE.md
```
</details>

## 📦 Instalación manual

```bash
git clone https://github.com/GabrielMarquez01/gearbox-skill.git
cd gearbox-skill
bash install.sh
```

O a mano: `SKILL.md` → `~/.claude/skills/gearbox/` · `statusline.sh` y `reset.sh` → `~/.claude/gearbox/` (con `chmod +x`) · registra `statusLine` y el hook `SessionStart` en `~/.claude/settings.json` · agrega la directiva Gearbox a `~/.claude/CLAUDE.md` (ver [install.sh](install.sh) como referencia exacta).

## 🗺️ Estructura

```
~/.claude/skills/gearbox/SKILL.md   ← el cerebro: tabla, protocolo, calibración, model watch
~/.claude/gearbox/statusline.sh     ← indicador azul (bash+sed puro)
~/.claude/gearbox/reset.sh          ← hook SessionStart → marcha default
~/.claude/gearbox/set.sh            ← ancla una marcha (gear/task/effort/model)
~/.claude/gearbox/log.sh            ← escribe la bitácora (events.jsonl / decisions.jsonl)
~/.claude/gearbox/state.json        ← marcha activa
~/.claude/gearbox/events.jsonl      ← set/reset — sin valor de calibración
~/.claude/gearbox/decisions.jsonl   ← bitácora de calibración (el dato que importa)
~/.claude/gearbox/log.jsonl.v1      ← archivo histórico pre-v3 (no borrar)
```

## 🤝 Contribuir y dar retroalimentación

**¿Te funcionó? ¿No te funcionó? Queremos saberlo.**

La próxima iteración del Gearbox se construye con evidencia real de la comunidad, no con suposiciones. Tres formas de participar:

- **⭐ Dale una estrella** si lo instalaste y te fue útil — es la señal más simple de que vale la pena seguir mejorándolo.
- **[Abre un issue](https://github.com/GabrielMarquez01/gearbox-skill/issues)** si encontraste un caso donde la recomendación estuvo mal, el statusline mintió, o hay una marcha que falta. Un caso real con contexto vale más que diez sugerencias abstractas.
- **[Manda un PR](https://github.com/GabrielMarquez01/gearbox-skill/pulls)** si tienes una calibración con evidencia, un port (PowerShell, Fish), o una traducción.

**¿Quieres recibir las actualizaciones?**
Dale **Watch → Releases only** al repo (botón arriba a la derecha). Cada iteración importante sale como release con notas de qué cambió y por qué — sin spam, solo cuando hay algo concreto.

> El Gearbox se itera igual que funciona: usar → medir con datos reales → mejorar solo lo que la evidencia señala.

## Licencia

[MIT](LICENSE) — Gabriel Marquez / [OpenGravity](https://github.com/GabrielMarquez01/OpenGravity), 2026.

---

<div align="center"><sub>⚙ <b>Gearbox</b> — evolución del Gearbox Protocol de OpenGravity · usar → medir → calibrar</sub></div>
