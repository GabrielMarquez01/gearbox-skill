# FUENTES — de dónde sale cada precio, ID y cifra de Gearbox

Actualizado: 2026-11-08 09:27 (America/Mexico_City).

Reconfirmación 2026-11-08: IDs y precios base de los cuatro modelos, incluidos ambos
tramos de Haiku, abiertos en la documentación oficial de modelos y precios. Los enlaces de
§1 y §2 se reconsultaron para este parche; las demás consultas conservan su fecha original.
El registro original de consultas corresponde al **2026-10-30** a la fuente oficial de cada proveedor. Si una tarifa o un modelo cambió después de esa fecha, la fuente manda sobre este archivo.
Citas literales en inglés tal como las devolvió la página; las traducciones al español del repo se marcan como «traducción nuestra / libre».

## 1. Precios (USD por millón de tokens, tarifa base de la API)

| Modelo | ID de API | Entrada | Salida | Fuente (URL · consulta de los cuatro modelos: 2026-11-08) | Dónde aparece en el repo |
|---|---|---:|---:|---|---|
| Fable 5.1 | `claude-fable-5-1` | $10 | $50 | https://platform.claude.com/docs/en/about-claude/models/overview · https://platform.claude.com/docs/en/about-claude/pricing (fila «Claude Fable 5.1») · https://claude.com/pricing · https://platform.claude.com/docs/en/models/fable-5-1/overview | `SKILL.md` (§Tabla de Marchas, §Model Watch), `README.md` (tabla de precios) |
| Opus 5.5 | `claude-opus-5-5` | $4 | $20 | https://platform.claude.com/docs/en/about-claude/pricing (fila «Claude Opus 5.5») | ídem |
| Sonnet 5.5 | `claude-sonnet-5-5` | $2 | $10 | https://platform.claude.com/docs/en/about-claude/pricing (fila «Claude Sonnet 5.5») | ídem |
| Haiku 5.5 (prompt ≤ 100 000 tokens) | `claude-haiku-5-5` | $0.10 | $0.50 | https://platform.claude.com/docs/en/about-claude/pricing: «Claude Haiku 5.5 (for prompts up to 100,000 tokens) … $0.10 / MTok … $0.50 / MTok» · claude.com/pricing: «Haiku 5.5 (≤100K-token prompts) $0.10 / $0.50» | ídem |
| Haiku 5.5 (prompt > 100 000 tokens) | `claude-haiku-5-5` | $0.50 | $2.50 | https://platform.claude.com/docs/en/about-claude/pricing: «Claude Haiku 5.5 (for prompts over 100,000 tokens) … $0.50 / MTok … $2.50 / MTok» | `SKILL.md`, `README.md` |
| Opus 5 (anterior, solo para comparar) | — | $5 | $25 | pricing (fila «Claude Opus 5») y claude.com/pricing («Legacy models») | `README.md` y `SKILL.md` («el Opus anterior costaba $5 / $25») |
| Sonnet 5 (anterior, solo para comparar) | — | $2 | $10 | pricing, nota 3: «The $2/$10 per million input/output token pricing for Claude Sonnet 5, announced at launch as introductory pricing through August 31, 2026, is now the standard price. The previously scheduled increase to $3/$15 … will not occur.» | `SKILL.md` §Model Watch (3) |

`prices.json` contiene estos cuatro IDs y tarifas desde el parche del 2026-11-08.
`input_long`, `output_long`, `relative_long` y `prompt_threshold` modelan el segundo tramo de Haiku.
Las tarifas son base de la API directa, USD por millón de tokens, sin caché ni recargos de residencia.
Las filas anteriores (Opus 5 y Sonnet 5) son históricas, consulta conservada del 2026-10-30.

Notas oficiales usadas:
- Lectura de caché: «prompt cache reads cost 10% of the base input price (2.5% on Claude Fable 5.1 and Claude Mythos 5.1, 5% on Claude Opus 5.5 and Claude Sonnet 5.5)» — models overview, nota *Pricing*. De ahí «del 90 % al 97.5 %» de descuento en `SKILL.md` (el 10 % de Haiku 5.5 sale de su fila: $0.01 sobre $0.10).
- Fable 5.1 «extends Claude Fable 5 at the same input and output prices, with cache reads at a quarter of the cost» (https://platform.claude.com/docs/en/models/fable-5-1/overview); lanzado «September 1, 2026».
- Haiku 5.5 se cobra por longitud de prompt: «Claude Haiku 5.5 is priced by prompt length: a request whose prompt is over 100,000 tokens pays higher prices» (pricing, §Long context pricing).
- Los demás modelos incluyen la ventana de 1M «at standard pricing» (pricing, §Long context pricing).

## 2. IDs, ventana, salida y esfuerzo por defecto (models overview, reconsulta 2026-11-08)

URL: https://platform.claude.com/docs/en/about-claude/models/overview

- Claude API ID: `claude-fable-5-1`, `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5` («Every Claude model ID is a pinned snapshot»).
- Contexto 1M y salida máxima 128K en los cuatro. Pensamiento: Fable 5.1 y Opus 5.5 «Adaptive (always on)»; Sonnet 5.5 y Haiku 5.5 «Adaptive».
- Esfuerzo por defecto en la API: Fable 5.1 `high` · Opus 5.5 `medium` · Sonnet 5.5 `high` · Haiku 5.5 `medium`.
- Recomendación de elección: «start with Claude Opus 5.5 for most workloads. Use Claude Fable 5.1 for demanding reasoning and long-horizon agentic work, or when your evals on Claude Opus 5.5 at higher effort still fall short» (citada en `SKILL.md`, traducción nuestra).

## 3. Esfuerzo y pensamiento

URL: https://platform.claude.com/docs/en/build-with-claude/effort (consultada 2026-10-30)
- Niveles `low`/`medium`/`high`/`xhigh`/`max` y sus descripciones (tabla «Effort levels»): `low` «Simpler tasks that need the best speed and lowest costs, such as subagents»; `medium` «Agentic tasks that require a balance of speed, cost, and performance»; `high` «Complex reasoning, difficult coding problems, agentic tasks»; `xhigh` «Long-running agentic and coding tasks (over 30 minutes)…»; `max` «Tasks requiring the deepest possible reasoning».
- «Most Claude models default to high effort …; Claude Opus 5.5 and Claude Haiku 5.5 default to medium.»
- Opus 5.5: «medium is the default (Claude Opus 5 and earlier Opus models default to high, so a request that omits effort runs one level lower …)»; «Requests that set thinking: {"type": "disabled"} return a 400 error at every effort level».
- Sonnet 5.5: `between_tools` es lo más bajo, «At xhigh or max, a request with it returns a 400 error»; Haiku 5.5: `disabled` permitido «at high effort or below»; con `low` en prompts largos de agente «the model is more likely to skip a search, stop early, or skip a check».
- «Run an effort sweep on your own evals rather than carrying settings over from an earlier model» (citada en `SKILL.md`, traducción libre).
- «At high and above, set a large max_tokens. It's a hard limit on total output (thinking plus response text)».
- Sobre `max` (guía de Opus 4.7/4.8 en la misma página): «can lead to overthinking».

URL: https://platform.claude.com/docs/en/build-with-claude/thinking — «the tokens Claude spends reasoning are billed as output tokens … and they count toward max_tokens» (de ahí «el razonamiento se factura como salida»).

## 4. Claude Code: alias, esfuerzo, plan por defecto

URL: https://code.claude.com/docs/en/model-config (consultada 2026-10-30; se leyeron los primeros 100 000 de 129 779 caracteres)
- Alias `default`, `best`, `fable`, `sonnet`, `opus`, `haiku`, `sonnet[1m]`, `opus[1m]`, `opusplan` («uses opus during plan mode, then switches to sonnet for execution»).
- Resolución en la API de Anthropic: opus → Opus 5.5, sonnet → Sonnet 5.5, haiku → Haiku 5.5; el alias `fable` «resolves to Fable 5.1» salvo `ANTHROPIC_DEFAULT_FABLE_MODEL` (y salvo sesiones de gateway). En otros proveedores de nube la tabla muestra versiones anteriores para `sonnet`/`haiku` (y Foundry para `opus`).
- Esfuerzo: «`/effort`, `--effort`, `CLAUDE_CODE_EFFORT_LEVEL`, `effortLevel` (low, medium, high, xhigh; «max isn't accepted as a level in either key»)». Por defecto en Claude Code: «high on most models. Opus 5.5, Sonnet 5.5, and Haiku 5.5 default to medium».
- Modelo por defecto en Pro, Max, Team, Enterprise y API de Anthropic: Opus 5.5.
- Fijar versión: nombre completo (`claude-opus-5-5`) o `ANTHROPIC_DEFAULT_*_MODEL`; los alias «update over time».
- Nota de discrepancia declarada: para Sonnet 5.5 la doc de la API dice `high` por defecto y la de Claude Code dice `medium`; por eso `SKILL.md` no afirma un valor único («el esfuerzo por defecto depende del modelo y del producto: fíjalo»).

## 4b. Claude Code: payload del statusline (para `statusline.sh` y el guardián)

URL: https://code.claude.com/docs/en/statusline (reconsultada 2026-11-08 para campos de cupo y longitud)
- `context_window.total_input_tokens`: «Token counts currently in the context window, from the most recent API response. Input includes cache reads and writes». El parche selecciona `relative_long` de Haiku 5.5 para prompts > 100 000 tokens a partir de ese campo; si falta una longitud válida, omite el multiplicador.
- `effort.level`: «…Absent when the current model does not support the effort parameter». El parche muestra `?` cuando tampoco hay esfuerzo guardado y usa `effort=auto` por defecto en `set.sh`.
- `rate_limits.five_hour.used_percentage`, `rate_limits.seven_day.used_percentage` (0–100, pueden ser decimales) y `rate_limits.five_hour.resets_at`, `rate_limits.seven_day.resets_at`: «Unix epoch seconds when the 5-hour or 7-day rate limit window resets»; `session_id`: «Unique session identifier».
- `rate_limits`: «appears only for claude.ai Pro, Max, and Ultra subscribers, or behind a Claude apps gateway…; it appears only after the first API response in the session. Each window … may be independently absent».
- La doc menciona `ultrathink` («not one that a skill, a subagent, or `ultrathink` set»): existe como mecanismo, pero no documenta su efecto en los modelos 5.5; por eso G3.5 usa `/effort`.

Registro histórico: https://api.github.com/repos/GabrielMarquez01/gearbox-skill/commits?path=prices.json (vía `gh api`, 2026-10-30): tres commits que tocan `prices.json` (2026-07-06, 2026-07-13, 2026-07-25). No se reconsultó la red en esta actualización documental.

Comportamiento del parche del 2026-11-08 (cubierto por `tests/test_regressions.py`):
- El catálogo contiene los cuatro modelos actuales; el lector JSON acepta formato multilínea.
- El statusline solo acepta porcentajes finitos entre 0 y 100 y `resets_at` futuro.
  Escribe un snapshot completo, atómico, con permisos 600 y sello local `updated_at`.
- El guardián exige antigüedad entre 0 y 300 segundos y reset futuro; trabaja con un
  único snapshot por invocación. Solo anuncia recuperación con otra lectura posterior
  de la misma sesión, porcentaje <50. Una sesión registrada filtra otras sesiones.
- El TTL de 300 segundos y el truncamiento de porcentajes son decisiones del parche,
  no cifras atribuidas al proveedor. El cron documentado corre cada tres minutos.
- `install.sh` conserva precios existentes. La migración por huellas y `prices.json.nuevo`
  siguen fuera de este parche; quien actualice una instalación previa debe revisar su catálogo.
- UTF-8 inválido se descarta; comillas, barras y controles se escapan mediante JSON.

## 5. Cálculos derivados (aritmética propia, reproducible)

Entradas: tarifas de §1. Supuestos del ejemplo (del autor, declarados como supuestos en el README): tarea de 20 000 tokens de entrada y 3 000 de salida; mezcla hipotética 40 % Haiku 5.5 · 40 % Sonnet 5.5 · 15 % Opus 5.5 · 5 % Fable 5.1.

| Cálculo | Fórmula | Resultado |
|---|---|---|
| Costo por tarea | 0.02 × entrada + 0.003 × salida | Fable 5.1 $0.350 · Opus 5.5 $0.140 · Sonnet 5.5 $0.070 · Haiku 5.5 $0.0035 |
| Tareas con $100 | 100 / costo, redondeo hacia abajo | 285 · 714 · 1 428 · 28 571 |
| Costo de la mezcla | 0.4×0.0035 + 0.4×0.070 + 0.15×0.140 + 0.05×0.350 | $0.0679 → 1 472 tareas con $100; 2.06× frente a «todo Opus 5.5», 1.03× frente a «todo Sonnet 5.5», 5.15× frente a «todo Fable 5.1» |
| Multiplicador `relative` | precio de entrada ÷ $2 (Sonnet 5.5); la salida guarda la misma razón | 0.05 · 1 · 2 · 5 (Haiku, Sonnet, Opus, Fable); `relative_long` Haiku 5.5 = 0.50 ÷ 2 = 0.25 |
| Diferencia de salida más barato–más caro | $50 ÷ $0.50 | 100× |

Los números se recalcularon con Python (script de una pasada) antes de escribirlos; coinciden con los del README.

## 6. Otros proveedores (solo nombres/flags verificados; no se publica ninguna tarifa)

- Google — modelos Gemini: https://ai.google.dev/gemini-api/docs/models («Last updated 2026-10-28 UTC»): «Gemini 4 Argon (`gemini-4-argon`) … New Stable … flagship reasoning model with a unified 1M context window»; «Gemini 3.8 Flash (`gemini-3.8-flash`) … New Stable». Respalda la mención ya existente a Gemini 4 Argon en `docs/LECCIONES-MULTI-MOTOR-2026-10.md`. En `SKILL.md` los nombres de modelo de otros proveedores son **marcadores** (`proveedor-A:modelo-grande`), no nombres reales.
- Google — Antigravity: https://antigravity.google/ (2026-10-30): describe «Antigravity CLI»; no lista comando de instalación en la página; blog «Gemini 4 Argon in Google Antigravity (Oct 13, 2026)». La URL del instalador `https://antigravity.google/cli/install.sh` devolvió HTTP 200, `content-type: application/x-sh` y un script «Antigravity CLI - Unix Bootstrapper Script» (se leyeron solo los primeros 300 bytes; **no se ejecutó**).
- OpenAI — Codex: https://learn.chatgpt.com/docs/models (redirección permanente desde developers.openai.com/codex/models): modelos citados por la página `gpt-6-astra`, `gpt-6.1-sol`, `gpt-6.1-terra`, `gpt-6-luna`; selección con `-m/--model` y `config.toml`. **No se publican en `README.md` ni en `SKILL.md`** (el SKILL usa marcadores). Límites de uso: la página remite al Help Center y no los detalla — por eso el repo no publica ninguna cifra de cupo.
- CLIs locales (`--help`, 2026-10-30): `codex exec --help` confirma `-s, --sandbox <read-only|workspace-write|danger-full-access>`, `-m, --model` y que si hay prompt y stdin entubado «stdin is appended as a `<stdin>` block» (base de la nota `< /dev/null`); `agy --help` confirma `--sandbox`, `--print/-p`, `--model`, `--effort (low|medium|high|xhigh|max)`.
