# Gearbox Launch Notes

Material para compartir Gearbox sin prometer de mas. Copia, pega y ajusta al tono del canal.

## Mensaje central

Gearbox no es otro statusline. Es un recomendador para Claude Code: te ayuda a decidir cuando usar Haiku, Sonnet, Opus o Fable 5 antes de gastar tokens o limites.

## Claim seguro

- Independiente, open-source y no oficial de Anthropic.
- No cambia automaticamente el modelo principal; recomienda el comando exacto.
- Fable 5 no es para todo: es para arquitectura, infraestructura, contexto grande y decisiones ambiguas.
- La ventana hasta 2026-07-07 viene de Anthropic: inclusion hasta 50% de limites semanales para Pro, Max, Team y algunos Enterprise; despues depende de usage credits.

Fuentes:
- https://www.anthropic.com/news/redeploying-fable-5
- https://code.claude.com/docs/en/model-config
- https://platform.claude.com/docs/en/about-claude/models/overview

## Imagenes recomendadas

Usar en este orden:

1. `assets/banner.svg` como imagen principal.
2. `assets/demo.svg` como segunda imagen o comentario de seguimiento.
3. Screenshot del README mostrando "No es otro statusline" y "Ventana Fable 5".
4. Screenshot terminal con la barra: `Gearbox · Fable 5 · max`.

Evitar imagenes con claims de ahorro garantizado. Mejor mostrar decision y claridad.

## Post para SaaS Factory

Titulo sugerido:

```text
Gearbox: una skill para usar mejor Claude Code antes de quemar tokens
```

Texto:

```text
Comunidad, les comparto algo que construi para resolver un problema muy concreto usando Claude Code:

no siempre necesitamos el modelo mas caro.

Gearbox es una skill/recomendador para Claude Code que clasifica la tarea en "marchas":

G0: rutina -> Haiku / subagentes
G1-G2: contenido y ejecucion -> Sonnet
G3: planeacion -> opusplan
G4: critico -> Opus
G5: arquitectura grande -> Fable 5

La idea no es automatizar por humo ni decir "usa Fable para todo".
La idea es decidir mejor antes de gastar: cuando bajar, cuando mantener y cuando subir.

Tambien agregue una regla especial para Fable 5:
usarlo para arquitectura, infraestructura, decisiones multi-repo, root-cause dificil y planes de producto grandes.
No usarlo para copy, fixes pequeños, logs o tareas que Sonnet puede ejecutar bien.

Contexto oportuno:
Anthropic anuncio que Fable 5 esta incluido hasta 50% de limites semanales para ciertos planes hasta el 2026-07-07. Por eso conviene usarlo con intencion, no quemarlo en tareas pequeñas.

Repo:
https://github.com/GabrielMarquez01/gearbox-skill

Me interesa feedback de quienes usan Claude Code en serio:
1. ¿que tareas ustedes mandarian a Fable?
2. ¿que reglas agregarian para no sobrepagar modelos?
3. ¿les serviria una bitacora semanal de ahorro/retrabajo?
```

Primer comentario:

```text
Nota honesta: Gearbox no es oficial de Anthropic y no cambia automaticamente el modelo principal. Recomienda el comando exacto y deja el cambio en manos del usuario. La parte automatica posible es delegar rutina a modelos mas baratos/subagentes cuando aplica.
```

## Post para LinkedIn

Version principal:

```text
Estoy construyendo una pequeña herramienta open-source para una pregunta que cada vez importa mas:

¿cuando conviene usar el modelo mas poderoso y cuando solo estamos quemando tokens?

Se llama Gearbox.

Es una skill para Claude Code que funciona como recomendador de modelo y esfuerzo:

- Haiku para rutina
- Sonnet para ejecucion diaria
- opusplan para planear con Opus y ejecutar con Sonnet
- Opus para problemas criticos
- Fable 5 para arquitectura, infraestructura, contexto grande y decisiones ambiguas

Lo importante: no promete magia.

Gearbox no cambia el modelo principal por ti.
Te dice que marcha conviene, por que, cuanto cuesta o ahorra, y el comando exacto para cambiar.

El punto no es "usar Fable 5 para todo".
El punto es usar Fable 5 donde realmente tiene sentido:

- blueprint de producto o ecosistema completo
- infraestructura y tradeoffs dificiles
- analisis multi-repo
- root-cause de bugs complejos
- convertir una vision ambigua en plan ejecutable

Y dejar a Sonnet/Haiku lo que pueden resolver bien.

Esto se vuelve especialmente relevante porque Anthropic anuncio que Fable 5 esta incluido hasta 50% de limites semanales para ciertos planes hasta el 7 de julio de 2026; despues depende de usage credits.

La siguiente etapa de IA aplicada a negocio no es solo generar mas codigo.
Es orquestar mejor: modelo correcto, tarea correcta, costo correcto.

Repo:
https://github.com/GabrielMarquez01/gearbox-skill

Feedback bienvenido, especialmente de builders usando Claude Code en producto real.
```

Hashtags:

```text
#ClaudeCode #AIAgents #BuildInPublic #OpenSource #SaaS #AIForBusiness #SoftwareArchitecture
```

Menciones sugeridas si las tienes disponibles en LinkedIn:

```text
Anthropic, Claude, Daniel Carreon, SaaS Factory, OpenGravity
```

No fuerces menciones si LinkedIn no autocompleta el perfil correcto.

## Version corta para X

```text
Construí Gearbox: una skill open-source para Claude Code que recomienda cuándo usar Haiku, Sonnet, Opus o Fable 5.

No es otro statusline.
Es una capa de decisión: modelo correcto, tarea correcta, costo correcto.

Repo:
https://github.com/GabrielMarquez01/gearbox-skill
```

## Respuestas a dudas probables

Pregunta: ¿Esto ahorra dinero garantizado?

Respuesta:

```text
No lo venderia como ahorro garantizado. Lo venderia como mejor criterio de routing: bajar cuando la tarea es simple y subir cuando el retrabajo puede salir mas caro que el modelo.
```

Pregunta: ¿Por que no usar Fable para todo?

Respuesta:

```text
Porque Fable es mas caro y consume mas limites. Su mejor uso es arquitectura, infraestructura, contexto grande y decisiones ambiguas. Para ejecucion clara, Sonnet suele ser mejor equilibrio.
```

Pregunta: ¿Cambia modelos automaticamente?

Respuesta:

```text
No el modelo principal. Claude Code aun deja ese cambio en manos del usuario. Gearbox recomienda la marcha y el comando exacto. Lo automatico posible esta en rutina/subagentes y en opusplan.
```

Pregunta: ¿Es oficial?

Respuesta:

```text
No. Es open-source independiente. Usa capacidades oficiales de Claude Code: skills, statusLine, aliases de modelo, subagentes y comandos.
```

## KPI del lanzamiento

- 10 stars o installs.
- 3 comentarios con casos reales de uso.
- 1 PR o issue de mejora.
- 1 usuario reportando ahorro, menor retrabajo o mejor decision de modelo.

