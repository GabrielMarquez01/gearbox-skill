# 7 lecciones operando varios motores de IA en equipo (octubre 2026)

> Lo que aprendimos en OpenGravity coordinando Claude Code, Codex, Gemini (en Antigravity), sesiones en la nube y un servidor con agentes 24/7. Cada lección nació de un tropiezo real; aquí va la regla que dejó y cómo aplicarla.

| # | Lección | El tropiezo | La regla | Cómo se aplica |
|---|---|---|---|---|
| 1 | **Un motor pesado por máquina** | Dos auditorías lanzadas en paralelo en la misma PC murieron por falta de memoria | Todo motor externo entra por un «portero» que deja correr uno a la vez por máquina | Para paralelizar, usa otra máquina (un VPS) o la nube, no más procesos en la misma |
| 2 | **Quien audita no es quien produjo… ni del mismo proveedor** | Claude dentro de Antigravity revisando trabajo de Claude Code sigue siendo Claude revisando a Claude | El auditor siempre es de otro proveedor, y se declara el modelo en el veredicto | Trabajo de Claude → Codex o Gemini. Trabajo de Codex → Gemini o Claude |
| 3 | **La tabla de motores envejece sola** | El enrutador tenía los modelos escritos a mano y no supo que Gemini 4 Argon ya estaba disponible | El catálogo de modelos se mide, no se escribe a mano | Un revisor diario consulta los modelos reales (`agy models`, Codex, versión de Claude Code) y el changelog oficial. En Claude Code, los dynamic workflows permiten, con un mod en `agent.spawn`, cambiar el modelo de cada agente antes de arrancar: ahí se conecta tu tabla |
| 4 | **Un ajuste en vivo no es un ajuste** | Un techo de CPU/memoria puesto con `docker update` desapareció al recrear el contenedor tras actualizar la imagen; 15 días sin que nada lo notara | Lo que deba sobrevivir vive en la receta | Compose, unit de systemd o crontab versionado, y un vigilante que compare lo vivo contra la receta |
| 5 | **Vigilar desde dentro no basta** | El proveedor apagó el servidor 15 minutos; todo volvió solo (`restart: unless-stopped`, systemd), pero el vigilante interno se apagó con él y nadie se enteró | Al menos un vigilante corre FUERA de la máquina que vigila | Un chequeo externo de arranque reciente y de servicios vivos, con aviso |
| 6 | **La nube para planear, la PC para operar** | — | Planes y documentos largos en sesiones `claude --cloud`; lo que necesita navegador, servidor o llaves se queda local | `claude --cloud` pide terminal interactiva: si lo lanzas por script, hazlo dentro de `tmux` sin redirigir la salida |
| 7 | **La memoria es papel, no recuerdos** | Decisiones «recordadas» que nadie había escrito | Cada decisión queda escrita con la frase textual de quien la tomó; cada error deja una regla; si se repite, la regla se vuelve un candado (un hook que avisa o bloquea) | Lo que no quedó escrito, para el sistema no pasó |

## Qué cambió en el Gearbox a partir de esto
- **Gemini 4 Argon** entra como motor de frontera para auditar desde otro proveedor y para contexto muy largo; Codex y Claude Opus siguen para código de sistemas y terminal (según los benchmarks publicados por Google, aún sin verificación propia).
- En marcha: catálogo de motores medido a diario y conexión con los dynamic workflows oficiales de Claude Code.

¿Te ha funcionado otra cosa? Abre un issue con tu caso.
