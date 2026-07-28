# Auto-clasifica — complemento opcional

> **No se instala con el Gearbox y no está activo por defecto.** Es la versión mecánica
> de la clasificación: en vez de depender de que el modelo se acuerde de correr
> `set.sh`/`log.sh`, un hook se dispara solo en cada `Bash`/`Edit`/`Write`.

## El problema que resuelve

La clasificación manual (`set.sh`/`log.sh decision`) depende de que el modelo la recuerde
en cada turno. En una sesión larga real esto falló: 4 PRs llegaron a producción con **cero
clasificaciones registradas** en un hueco de ~23h, a pesar de un recordatorio de texto en
cada turno (`gearbox-recordatorio-turno.sh`, incluido en el core). El recordatorio ayuda,
pero sigue siendo una promesa — y una promesa del modelo no es un candado.

## Qué hace

Un hook `PreToolUse` que se dispara en cada `Bash`/`Edit`/`MultiEdit`/`Write` (las
herramientas que de verdad ejecutan o cambian algo) y clasifica por **palabras clave** en
el comando o archivo tocado:

| Señal | Marcha | Ejemplos |
|---|---|---|
| `rm -rf`, `drop table`, `reset --hard`, `push --force` | G5 | operaciones destructivas |
| `vercel --prod`, `dns_records`, `migration`, `stripe`, `.env` | G4 | deploy/infra/dinero real |
| `npm run build`, `git push`, `supabase`, `playwright` | G3 | ejecución sustancial |
| `git commit`, `mkdir`, `mv`, `cp` | G2 | ejecución simple |
| `ls`, `cat`, `grep`, `git log`, `git diff` | G0 | solo lectura |
| (nada hizo match) | G2 (Bash) / G3 (Edit-Write) | default conservador |

Cada clasificación actualiza `state.json` (así que tu statusline la refleja al instante,
sin que tengas que revisar nada) y queda en `decisions.jsonl` con
`"accion":"carril-automatico"` — el mismo valor que ya usa el hook de la tool `Agent` — para
que el contador de "racha sin clasificación manual" **no lo confunda con una clasificación
manual real** y te siga pidiendo la de mejor calidad cuando aplique.

## Qué NO hace (honestidad, no venta)

- **Es más tosco que el juicio del modelo.** Una heurística de palabras clave no entiende
  intención — solo texto. Úsalo como piso mínimo, no como reemplazo del juicio.
- **No bloquea nada.** Es de solo lectura/registro; si algo falla, sale en 0 en silencio y
  la herramienta corre igual. No es un gate de permisos.
- **No anuncia nada en el chat.** Actualiza el statusline y la bitácora; no imprime un
  mensaje visible en la conversación (eso sigue siendo trabajo del modelo, como buena
  práctica de sesión — ver `SKILL.md` §protocolo de anuncio).

## Instalación (manual — no la hace `install.sh`)

```bash
cp auto-clasifica/auto-clasifica.sh ~/.claude/hooks/gearbox-auto-clasifica.sh
chmod +x ~/.claude/hooks/gearbox-auto-clasifica.sh
```

Agrega a `~/.claude/settings.json` (dentro de `hooks.PreToolUse`, junto a lo que ya tengas):

```json
{
  "matcher": "Bash|Edit|MultiEdit|Write",
  "hooks": [
    { "type": "command", "command": "/home/TU_USUARIO/.claude/hooks/gearbox-auto-clasifica.sh", "timeout": 10 }
  ]
}
```

Reinicia Claude Code. Verifica que funciona con:

```bash
cat ~/.claude/gearbox/state.json    # debe reflejar tu última acción
tail -3 ~/.claude/gearbox/decisions.jsonl
```

## Personalización

La tabla de palabras clave vive en un solo bloque `case` dentro de `auto-clasifica.sh` —
ajústala a tu stack (otros gestores de paquetes, otro proveedor de nube, otro ORM). El
orden importa: la primera coincidencia gana, de más riesgoso a menos.
