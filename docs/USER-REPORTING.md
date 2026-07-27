# Cómo reportar resultados y mejorar Gearbox

## 1. Registra el resultado

Después de una tarea:

```bash
~/.claude/gearbox/gearbox.py feedback last accepted
```

Alternativas:

```bash
~/.claude/gearbox/gearbox.py feedback last rejected --reason incorrect_result
~/.claude/gearbox/gearbox.py feedback last rework --reason wrong_gear
~/.claude/gearbox/gearbox.py feedback last wrong-route --reason wrong_model
```

Los motivos permitidos son categorías cerradas. Los comentarios libres se
quedan locales.

## 2. Revisa antes de compartir

```bash
~/.claude/gearbox/gearbox.py telemetry preview
```

La vista previa muestra exactamente el cuerpo que saldría del equipo. Si aparece
un campo inesperado, no lo envíes y abre un issue sin copiar datos privados.

## 3. Participa voluntariamente

```bash
~/.claude/gearbox/gearbox.py telemetry enable community
~/.claude/gearbox/gearbox.py telemetry send
```

Si el programa comunitario aún no tiene endpoint productivo, el comando lo
indicará y no enviará nada.

## 4. Revoca o elimina la cola

```bash
~/.claude/gearbox/gearbox.py telemetry revoke
~/.claude/gearbox/gearbox.py telemetry purge
```

La revocación detiene envíos, elimina paquetes pendientes y rota el seudónimo.

## 5. Reporta un problema técnico

Abre un issue e incluye solamente:

- versión de Gearbox;
- sistema operativo;
- comando ejecutado;
- código de error;
- comportamiento esperado y observado;
- resultado de `gearbox.py doctor`.

No incluyas prompts, código privado, rutas, tokens, correos, capturas con datos
personales ni el contenido de la base SQLite.

## Métricas comunitarias útiles

- tasa de feedback completado;
- aceptación por ruta;
- retrabajo por marcha;
- overrides humanos;
- reportes bloqueados por privacidad;
- entregas confirmadas;
- precisión del routing por bandas.

La métrica principal es **costo por resultado aceptado**, no cantidad de eventos
ni volumen de tokens.
